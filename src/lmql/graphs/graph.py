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
from .solvers import Solver

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

    async def ainfer_branch(self, id: int, branching_call: List[defer_call]):
        """
        Invoked for a 'a() | b()'-style branching calls. This method determines
        which branch to explore and how its result should be inferred.
        """
        context: InferenceCall = get_graph_context()
        assert context is not None, "ainfer_branch() can only be called from within a graph context via lmql.infer(...)"

        candidate_instance_nodes = []
        for call in branching_call:
            node = self.qfct_to_node.get(call.query_function)

            candidate_instance_nodes.append(InstanceNode(
                node,
                predecessors=[],
                dangling=True,
                resumable=None,
                call=call,
                score=None,
            ))

        # 1. decide which candidate instance node to explore
        call_node: InstanceNode = context.solver.choice(candidate_instance_nodes, context)
        call = call_node.call

        # 2. record other calls as possible alternatives to be explored later
        other_options = [inode for inode in candidate_instance_nodes if inode is not call_node]

        # 3. infer branch result
        result = await self.ainfer_call(call.target, *call.args, **call.kwargs)

        # add dangling nodes/paths for all unexplored branches for this call
        if len(other_options) > 0:
            def exchange_result_with_resumable(query_resumable):
                nonlocal result, other_options
                for other_node in other_options:
                    # TODO: if a query function is used in different ways, this may be incorrect
                    call = other_node.call
                    node = self.qfct_to_node.get(call.query_function)
                    async def qresume(*args, __fresh__=False, **kwargs):
                        if __fresh__:
                            r = await self.ainfer(node, *call.args, unwrap=False, **call.kwargs)
                            return await query_resumable(r)
                        else:
                            return await query_resumable(*args, **kwargs)
                    
                    # make sure other option node can be resumed
                    other_node.resumable = qresume
                    # store other node in calling context and thus in instance graph
                    context.dangling_nodes.setdefault(id, []).append(other_node)
                return result
            return checkpoint(exchange_result_with_resumable)
        else:
            return result

    async def ainfer(self, node: QueryNode, *args, unwrap=True, **kwargs):
        """
        Infers the result of the given query node, assuming the 
        provided arguments and keyword arguments are the inputs.
        """
        assert node is not None, "Query node cannot be None"

        # check if this is a sub-query call
        context: InferenceCall = get_graph_context()
        
        # count query calls per node
        node.num_calls += 1

        # in new context, compute result and track inputs and outputs
        # as instance nodes and edges
        with InferenceCall(self, node, context.solver, args, kwargs) as call:
            if "cache" not in kwargs and self.caching_strategy == 'node':
                kwargs["cache"] = f"/tmp/lmql-graph-cache-{node.name}.tokens"
            
            # actually execute underlying query function
            result = await node.query_fct.__acall__(*args, **kwargs)
            score = 1.0
        
            # check if result has identity-mapped instance node
            if result_node := call.inputs_mapping.get(id(result)):
                score = result_node.score

            # otherwise check if result has been manually annotated with 
            # a score (e.g. a@0.1)
            elif value_score := call.value_scores.get(id(result)):
                score = value_score

            # create corresponding instance graph structure
            instance_node = InstanceNode(result, call.inputs, score=score)
            # register new instance node in calling context (as input to calling query)

            if context is not None:
                context.inputs.append(instance_node)
                context.inputs_mapping[id(result)] = instance_node

            # track instance node in query node
            node.add_instance(instance_node)

            # merge equivalent instance nodes
            node.merge_instances()

            if self.on_infer:
                self.on_infer()

            # create dangeling instance nodes for each alternative branch
            dangling_nodes = call.dangling_nodes
            for call_id, inodes in dangling_nodes.items():
                for inode in inodes:
                    inode.result.add_instance(inode)

            def exchange_result_for_resumable(outer_resumable):
                nonlocal result
                
                # create lifted dangling instance nodes using 'outer_resumable'
                for call_id, inodes in dangling_nodes.items():
                    for inode in inodes:
                        context.dangling_nodes.setdefault(call_id, []).append(lifted(
                            node,
                            defer_call(node.query_fct, *args, **kwargs),
                            outer_resumable,
                            [inode]
                        ))
                
                # also make call to sampled instance_node re-entrant (i.e. allows to re-sample
                # any instance node in the context of its caller)
                instance_node.resumable = outer_resumable

                if type(result) is checkpoint:
                    unwrapped_result = result(identity)
                    instance_node.result = unwrapped_result
                    return unwrapped_result
                return result
            
            # make sure calling context provides resumable in exchagne
            # for actual result
            checkpoint_result = checkpoint(exchange_result_for_resumable)

            # if 'unwrapping', caller does not expect 'checkpoint' and 
            # we stored lifted dangling nodes directly in the graph (calling
            # context is client or solver directly)
            if unwrap:
                # make sure dangling nodes are created
                checkpoint_result(identity)
                
                # add final edges for dangling nodes
                for call_id, inodes in context.dangling_nodes.items():
                    for inode in inodes:
                        context.node.add_instance(inode)
                return result
            
            return checkpoint_result

    async def acomplete(self, node: InstanceNode, solver, unwrap=True):
        assert node.dangling, "Cannot complete non-dangling instance nodes"
        assert node.resumable is not None, "Provided query node does not have a resumable"

        with InferenceCall(self, node, solver) as call:
            assert len(node.predecessors) <= 1, "a acomplete() call expects a linear predecessor chain"
            inputs = [await self.acomplete(p, solver=solver, unwrap=True) for p in node.predecessors]
            result = await node.resumable(*inputs, __fresh__=len(inputs) == 0)

            score = 1.0
            
            # check if result has identity-mapped instance node
            if result_node := call.inputs_mapping.get(id(result)):
                score = result_node.score

            # otherwise check if result has been manually annotated with 
            # a score (e.g. a@0.1)
            elif value_score := call.value_scores.get(id(result)):
                score = value_score

            if type(result) is checkpoint:
                result = result(node.resumable)

            node.result = result
            node.value_class = str(result)
            node.score = score
            node.dangling = False
            node.resumable = None
            if len(inputs) == 0:
                node.predecessors = call.inputs[0].predecessors
                node.query_node.instances.remove(call.inputs[0])

        return node.result
    
    def complete(self, node: InstanceNode, solver: Solver):
        return run_in_loop(self.acomplete(node, solver))

    def infer(self, node: QueryNode, *args, **kwargs):
        return run_in_loop(self.ainfer(node, *args, **kwargs))


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