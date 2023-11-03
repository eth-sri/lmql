from dataclasses import dataclass, field
from lmql.graphs.nodes import *
from itertools import product
from lmql.graphs.runtime import *
import random
import json
import asyncio
from lmql.runtime.loop import run_in_loop
from .printer import InferenceGraphPrinter
from typing import List, Union, Tuple, Optional
from lmql.runtime.resumables import resumable, identity
from lmql.graphs.inference_call import InferenceCall
from functools import partial
from .solvers import Solver, GraphCallAssertionError

def with_resumable(fct):
    async def wrapper(*args, unpack=False, **kwargs):
        call: InferenceCall = get_graph_context()
        async def handler(r):
            return await fct(*args, **kwargs, resumable=r, calling_context=call)
        
        if unpack:
            r = await handler(identity)
            while type(r) is checkpoint:
                r = await r(identity)
            return r
        else:
            return checkpoint(handler)
    return wrapper

class InferenceGraph:
    """
    An inference graph is a directed acyclic graph (DAG) of LMQL query functions
    allowing for the inference of query results based on the results of multiple 
    sub-queries.

    Execution is guided by an execution engine allowing to optimize for different 
    aspect of the inference process (e.g. reliabililty, consistency, cost, etc.).
    """

    def __init__(self, caching_strategy=None):
        # all instance and query nodes of this graph
        self.nodes: List[Union[QueryNode, InstanceNode]] = []
        self.caching_strategy = caching_strategy
        self.on_infer = None
        
        # mapping of LMQLQueryFunction to QueryNodes
        self.qfct_to_node = {}

    @classmethod
    def from_query(cls, query_fct, **kwargs):
        graph = cls(**kwargs)
        qnode = _build_graph(query_fct, graph=graph, instance_pool={})
        return graph, qnode

    def add(self, node):
        self.nodes.append(node)
        self.qfct_to_node[node.query_fct] = node
    
    def to_json(self):
        return InferenceGraphPrinter().to_json(self)

    async def ainfer_call(self, fct: callable, *args, **kwargs):
        """
        Invoked for a regular a() query function call, this method 
        determines how to infer the result of the call.
        """
        qfct = query_function(fct)
        if qfct is None:
            return await call_raw(fct, *args, **kwargs)
        node = self.qfct_to_node.get(qfct)

        # call actual ainfer method
        return await self.ainfer(node, *args, unwrap=False, **kwargs)

    async def debug_out(self):
        if self.on_infer:
            self.on_infer()

            
    def complete(self, node: InstanceNode, solver: Solver):
        return run_in_loop(self.acomplete(node, solver))

    def infer(self, node: QueryNode, *args, **kwargs):
        return run_in_loop(self.ainfer(node, *args, **kwargs))

    @with_resumable
    async def ainfer_branch(self, id: int, branching_call: List[defer_call], resumable: resumable, calling_context: InferenceCall):
        """
        Invoked for a 'a() | b()'-style branching calls. This method determines
        which branch to explore and how its result should be inferred.
        """
        assert resumable is not None, "ainfer_branch must be called with a resumable"
        assert calling_context is not None, "ainfer_branch must be called with a call"

        candidate_instance_nodes = []
        for dcall in branching_call:
            node = self.qfct_to_node.get(dcall.query_function)

            candidate_instance_nodes.append(InstanceNode(
                node,
                predecessors=[],
                dangling=True,
                resumable=resumable,
                call=dcall,
                score=None,
                query_node=node
            ))

        # 1. decide which candidate instance node to explore
        chosen_call_node: InstanceNode = calling_context.solver.choice(candidate_instance_nodes, calling_context)
        chosen_call = chosen_call_node.call

        # 2. record other calls as possible alternatives to be explored later
        other_options = [inode for inode in candidate_instance_nodes if inode is not chosen_call_node]

        # 3. infer branch result
        result = await self.ainfer_call(chosen_call.target, *chosen_call.args, **chosen_call.kwargs)

        # create dangling nodes in the graph for all other options
        for o in other_options:
            o.query_node.add_instance(o)
            calling_context.dangling_nodes.append(o)

        await self.debug_out()
        
        return result

    @with_resumable
    async def ainfer(self, node: QueryNode, *args, return_node = False, resumable: resumable = None, calling_context: InferenceCall = None, **kwargs):
        """
        Infers the result of the given query node, assuming the 
        provided arguments and keyword arguments are the inputs.
        """
        assert resumable is not None, "ainfer must be called with a resumable"
        assert calling_context is not None, "ainfer must be called with a call"

        with InferenceCall(self, node, calling_context.solver, args, kwargs) as call:
            result = await node.query_fct.__acall__(*args, **kwargs)

            # create instance node for this result
            instance_node = InstanceNode(
                result,
                predecessors=call.inputs,
                dangling=False,
                resumable=resumable,
                call=call,
                score=None,
                query_node=node
            )
            node.add_instance(instance_node)

            # check for dangling nodes from sub-calls, to be lifted to this call level
            for dangling_node in call.dangling_nodes:
                lnode = lifted(node, defer_call(node.query_fct, *args, **kwargs), resumable, [dangling_node])
                node.add_instance(lnode)
                calling_context.dangling_nodes.append(lnode)

            # register result as input to calling context
            calling_context.inputs.append(instance_node)

            return result

    @with_resumable
    async def acomplete(self, node: InstanceNode, unwrap=True, resumable: resumable = None, calling_context: InferenceCall = None):
        """
        Like ainfer for dangling nodes (e.g. partially sampled paths).
        """
        assert resumable is not None, "acomplete must be called with a resumable"
        assert calling_context is not None, "acomplete must be called with a call"

        with InferenceCall(self, node.query_node, calling_context.solver, node.call.args, node.call.kwargs) as call:
            if len(node.predecessors) == 0:
                qfct = node.call.query_function
                result = await qfct.__acall__(*node.call.args, **node.call.kwargs)
                # result = await self.ainfer(node.query_node, *node.call.args, return_node=True, **node.call.kwargs)
                replayed = False
            else:
                predecessors_values = [await self.acomplete(pred) for pred in node.predecessors]
                while any([type(p) is checkpoint for p in predecessors_values]):
                    for i in range(len(predecessors_values)):
                        if type(predecessors_values[i]) is checkpoint:
                            predecessors_values[i] = await predecessors_values[i](node.resumable)
                print("resume with", [predecessors_values])
                result = await node.resumable(*predecessors_values)
                replayed = True

            async def rewrite_node_data(resumable):
                """
                Executed once continuation of this acomplete call was 
                determined (actual results only become available after
                all predecessors have been completed).
                """
                nonlocal result, call

                while type(result) is checkpoint:
                    result = await result(resumable)

                # check for dangling nodes from sub-calls, to be lifted to this call level
                for dangling_node in call.dangling_nodes:
                    lnode = lifted(node.query_node, call, resumable, [dangling_node])
                    node.query_node.add_instance(lnode) # dangling_node)
                    calling_context.dangling_nodes.append(lnode)

                # register result as input to calling context
                calling_context.inputs.append(node)
                
                if not replayed:
                    node.predecessors = call.inputs

                node.dangling = False
                node.set_result(result)

                return result
            
            return checkpoint(rewrite_node_data)

def _build_graph(query_fct_or_ref: Union[LMQLQueryFunction, Tuple[str, LMQLQueryFunction]], graph, instance_pool):
    """
    Constructs an LMQL inference graph from the call hierarchy 
    of the given query function.
    """
    if type(query_fct_or_ref) is tuple:
        query_fct = query_fct_or_ref[1]
        name = query_fct_or_ref[0]
    else:
        query_fct = query_fct_or_ref
        name = query_fct.name if type(query_fct) is LMQLQueryFunction else query_fct.__name__
    
    if query_fct in instance_pool:
        return instance_pool[query_fct]
    else:
        query_node = QueryNode(name, query_fct)
        instance_pool[query_fct] = query_node
    
    # non-query functions are also QueryNodes, but we do not 
    # track their dependencies
    if query_function(query_fct) is None:
        return query_fct

    query_node.merging_strategy = query_fct.extra_args.get("merge", None)

    # get compiler-determined query dependencies
    factored_dependencies = query_fct.resolved_query_dependencies()
    
    # nothing to do if there are no dependencies
    if len(factored_dependencies) == 0:
        graph.add(query_node)
        return query_node
    
    # for alternative dependency sets (e.g. a,b or a,d), enumerate all combinations
    # of dependencies and add corresponding edges to the graph
    factored_dependencies = [[dep] if type(dep) is not list else dep for dep in factored_dependencies]
    for deps in product(*factored_dependencies):
        edge = QueryEdge([_build_graph(pred, graph=graph, instance_pool=instance_pool) for pred in deps], target=query_node)
        query_node.incoming.append(edge)
    graph.add(query_node)
    
    return query_node