from dataclasses import dataclass, field
from lmql.graphs.nodes import *
from itertools import product
from lmql.graphs.runtime import *
import random
import json
from lmql.runtime.loop import run_in_loop
from .printer import InferenceGraphPrinter
from typing import List, Union
from lmql.graphs.inference_call import InferenceCall

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
        
        # mapping of LMQLQueryFunction to QueryNodes
        self.qfct_to_node = {}

    @classmethod
    def from_query(cls, query_fct, **kwargs):
        graph = cls(**kwargs)
        qnode = _build_graph(query_fct, graph=graph)
        return graph, qnode

    def add(self, node):
        self.nodes.append(node)
        self.qfct_to_node[node.query_fct] = node
    
    def to_json(self):
        return InferenceGraphPrinter().to_json(self)

    async def ainfer_call(self, fct: callable, *args, other_options=None, **kwargs):
        """
        Invoked for a regular a() query function call, this method 
        determines how to infer the result of the call.
        """
        qfct = query_function(fct)
        if qfct is None:
            return await call_raw(fct, *args, **kwargs)
        node = self.qfct_to_node.get(qfct)

        # check for existing previously computed (deferred) ainfer result
        context = get_graph_context()
        arg_repr = str(args) + str(kwargs)
        
        options = [defer_call(fct, *args, **kwargs)] + (other_options or [])
        
        if context is not None:
            previously_deferred = context.node.branches.get(arg_repr, [])
            options = options + previously_deferred
        
        print(context.node.name if context is not None else "<root>", ": ", options, sep="")

        # call actual ainfer method
        result = await self.ainfer(node, *args, other_options=other_options, **kwargs)

        # check for value alternatives recorded for 'result'
        if context is not None:
            if alternatives := context.value_alternatives[id(result)]:
                context.node.branches.setdefault(arg_repr, []).extend(alternatives)
        # print("node.branches", node, node.branches)

        return result

    async def ainfer_branch(self, id: int, branching_call: List[defer_call]):
        """
        Invoked for a 'a() | b()'-style branching calls. This method determines
        which branch to explore and how its result should be inferred.
        """
        context: InferenceCall = get_graph_context()
        assert context is not None, "ainfer_branch() can only be called from within a graph context via lmql.infer(...)"

        # 1. decide which branch to explore
        call: defer_call = random.choice(branching_call)
        # record other calls as possible alternatives to be explored later
        other_options = [c for c in branching_call if c is not call]

        # 2. check whether to re-sample branch or use cached result
        pass

        # 3. infer branch result
        return await self.ainfer_call(call.target, *call.args, **call.kwargs, other_options=other_options)

    async def ainfer(self, node: QueryNode, *args, other_options=None, **kwargs):
        """
        Infers the result of the given query node, assuming the 
        provided arguments and keyword arguments are the inputs.
        """
        # check if this is a sub-query call
        context: InferenceCall = get_graph_context()
        
        # count query calls per node
        node.num_calls += 1

        # in new context, compute result and track inputs and outputs
        # as instance nodes and edges
        with InferenceCall(self, node) as call:
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
                context.value_alternatives[id(result)] = other_options or call.value_alternatives.get(id(result))

            # track instance node in query node
            node.add_instance(instance_node)

            # merge equivalent instance nodes
            node.merge_instances()
            
            return result

    def infer(self, node: QueryNode, *args, **kwargs):
        return run_in_loop(self.ainfer(node, *args, **kwargs))


def _build_graph(query_fct, graph):
    """
    Constructs an LMQL inference graph from the call hierarchy 
    of the given query function.
    """
    name = query_fct.name if type(query_fct) is LMQLQueryFunction else query_fct.__name__
    query_node = QueryNode(name, query_fct)
    
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
        edge = QueryEdge([_build_graph(pred, graph=graph) for pred in deps], target=query_node)
        query_node.incoming.append(edge)
    graph.add(query_node)
    
    return query_node