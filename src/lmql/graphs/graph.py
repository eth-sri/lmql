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
from functools import wraps
class TracingRuntime:
    def __init__(self, graph):
        self.captured = []
        self.dangling = []
        self.graph = graph
        self.finalized = False
        
        # indicates to interpreter to produce query resumable 
        # before each function call
        self.resumable = True

    def finalize(self):
        self.finalized = True

    def ensure_nonfinalized(self):
        if self.finalized:
            raise ValueError("call to finalized runtime")

    async def call(self, fct, *args, resumable=None, **kwargs):
        self.ensure_nonfinalized()
        assert resumable is not None, "cannot handle runtime calls without resumable"
        
        result = await self.graph.ainfer_call(fct, *args, **kwargs)
        
        if fct is branch:
            instance_node, alternatives = result
            
            self.dangling += alternatives
            self.captured.append((defer_call(fct, *args, **kwargs), instance_node))

            self.ensure_nonfinalized()

            for d in self.dangling:
                d.resumable = resumable
            
            instance_node.resumable = resumable

            if type(instance_node.result) is GraphCallAssertionError:
                raise instance_node.result 
            return instance_node.result
        elif type(result) is tuple:
            instance_node, dangling_nodes = result
            self.dangling += dangling_nodes
            self.captured.append((defer_call(fct, *args, **kwargs), instance_node))

            self.ensure_nonfinalized()

            for d in dangling_nodes:
                d.resumable = resumable
            
            instance_node.resumable = resumable
            
            if type(instance_node.result) is GraphCallAssertionError:
                raise instance_node.result
            return instance_node.result
        else:
            return result

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
        if fct is branch:
            return await self.ainfer_branch(*args, **kwargs)
        if qfct is None:
            return await call(fct, *args, **kwargs)
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

    async def ainfer_branch(self, id: int, branching_call: List[defer_call]):
        """
        Invoked for a 'a() | b()'-style branching calls. This method determines
        which branch to explore and how its result should be inferred.
        """
        context: InferenceCall = get_graph_context()
        
        candidates = []
        for dcall in branching_call:
            qnode = self.qfct_to_node.get(dcall.query_function)
            assert qnode is not None, f"Query function {dcall.query_function} is not part of the graph."
            candidates.append(InstanceNode(None, [], None, call=dcall, dangling=True, query_node=qnode, resample=True))

        chosen_candidate = context.solver.choice(candidates, context)
        alternatives = [c for c in candidates if c is not chosen_candidate]
        for a in alternatives:
            a.query_node.add_instance(a)

        result, dangling = await self.ainfer(chosen_candidate.query_node, *dcall.args, **dcall.kwargs)

        return result, dangling + alternatives

    async def ainfer(self, node: QueryNode, *args, instance_node=None, **kwargs):
        """
        Infers the result of the given query node, assuming the 
        provided arguments and keyword arguments are the inputs.
        """
        tracing_runtime = TracingRuntime(self)
        call = defer_call(node.query_fct, *args, **kwargs)
        
        try:
            result = await node.query_fct.__acall__(*args, **kwargs, runtime=tracing_runtime)
        except AssertionError as e:
            result = GraphCallAssertionError(str(e))
        except GraphCallAssertionError as e:
            result = e

        tracing_runtime.finalize()

        inputs = [node for call, node in tracing_runtime.captured]
        
        if instance_node is None:
            instance_node = InstanceNode(result, inputs, 1.0, call=call, query_node=node)
        instance_node.set_result(result)
        instance_node.predecessors = inputs
        instance_node.score = 1.0
        instance_node.call = call
        instance_node.query_node = node
        instance_node.dangling = False

        dangling_nodes = tracing_runtime.dangling
        lifted_dangling = [lifted(node, call, resumable=None, predecessors=[n]) for n in dangling_nodes]
        for ld in lifted_dangling:
            node.add_instance(ld)

        if type(result) is GraphCallAssertionError:
            instance_node.error = result
            if result.retry_node is None:
                retry_node = InstanceNode(
                    None, 
                    inputs, 
                    None, 
                    dangling=True, 
                    call=call, 
                    query_node=node,
                    resample=True,
                    resumable=instance_node.resumable
                )
                result.retry_node = retry_node
                lifted_dangling.append(retry_node)
                node.add_instance(retry_node)
        
        # record as instance nodes in the graph
        node.add_instance(instance_node)
        node.merge_instances()

        return instance_node, lifted_dangling

    async def acomplete(self, instance_node: InstanceNode):
        """
        Like ainfer for dangling nodes (e.g. partially sampled paths).
        """

        # view as instance of its query node
        node = instance_node.query_node
        args = instance_node.call.args
        kwargs = instance_node.call.kwargs
        call = defer_call(node.query_fct, *args, **kwargs)

        # use cached value for non-dangling nodes in path to complete
        if not instance_node.dangling:
            print("use cached value")
            if instance_node.error is not None:
                raise ValueError("failed node must have at least one dangling node (retry): {} {}".format(instance_node, instance_node.error.retry_node))
            return instance_node, []
        
        if instance_node.resample:
            node, dangling = await self.ainfer(instance_node.query_node, *args, instance_node=instance_node, **kwargs)
            return node, dangling

        tracing_runtime = TracingRuntime(self)
        
        try:
            # resumable to transform a predecessor result value to an inference
            # result for the current node

            if len(instance_node.predecessors) != 1:
                raise ValueError("dangling node must have exactly one predecessor")
            
            predecessor = instance_node.predecessors[0]

            # simulate calls that happened so far
            result_node, dangling = await self.acomplete(predecessor)
            tracing_runtime.dangling += dangling
            tracing_runtime.captured.append((predecessor.call, result_node))
            # re-wire (potentially new) predecessor to result node
            instance_node.predecessors = [result_node]

            if result_node.error is not None:
                if len(dangling) == 0:
                    raise ValueError("failed node must have at least one dangling node (retry): {} {}".format(result_node, result_node.error.retry_node))
                raise result_node.error

            if predecessor.resumable is None:
                raise ValueError("predecessor of any dangling node must have a resumable: {} --[missing]--> {}".format(predecessor, instance_node))

            try:
                # resume current node where it was left off
                result = await predecessor.resumable(result_node.result, runtime=tracing_runtime)
            except GraphCallAssertionError as e:
                print("error during resume")
                raise e
        # handle assertions as in regular ainfer
        except AssertionError as e:
            result = GraphCallAssertionError(str(e))
        except GraphCallAssertionError as e:
            result = e
        
        tracing_runtime.finalize()

        instance_node.set_result(result)
        instance_node.score = 1.0
        instance_node.dangling = False
        inputs = [node for call, node in tracing_runtime.captured]

        dangling_nodes = tracing_runtime.dangling
        # set resumables for dangling nodes to resumables of predecessor 
        for dn in dangling_nodes:
            dn.resumable = predecessor.resumable

        lifted_dangling = [lifted(node, call, resumable=None, predecessors=[n]) for n in dangling_nodes]
        for ld in lifted_dangling:
            node.add_instance(ld)

        if type(result) is GraphCallAssertionError:
            instance_node.error = result
            if result.retry_node is None:
                retry_node = InstanceNode(None, 
                    inputs, None, 
                    dangling=True, 
                    resumable=instance_node.resumable,
                    call=call, 
                    query_node=node, 
                    resample=instance_node.resample
                )
                result.retry_node = retry_node
                lifted_dangling.append(retry_node)
                node.add_instance(retry_node)
        
        # record as instance nodes in the graph
        node.add_instance(instance_node)
        node.merge_instances()

        return instance_node, lifted_dangling

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