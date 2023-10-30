from dataclasses import dataclass, field
from lmql.graphs.nodes import *
from itertools import product
from lmql.graphs.runtime import *
import random
import json
from lmql.runtime.loop import run_in_loop
from .printer import to_json
from typing import List, Union

class InferenceGraph:
    """
    An inference graph is a directed acyclic graph (DAG) of LMQL query functions
    allowing for the inference of query results based on the results of multiple 
    sub-queries.

    Execution is guided by an execution engine allowing to optimize for different 
    aspect of the inference process (e.g. reliabililty, consistency, cost, etc.).
    """

    def __init__(self):
        # all instance and query nodes of this graph
        self.nodes: List[Union[QueryNode, InstanceNode]] = []
        
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
        return to_json(self)

    async def ainfer_call(self, fct, *args, **kwargs):
        """
        Invoked for a regular a() query function call, this method 
        determines how to infer the result of the call.
        """
        qfct = query_function(fct)
        if qfct is None:
            return await call_raw(fct, *args, **kwargs)
        node = self.qfct_to_node.get(qfct)
        return await self.ainfer(node, *args, **kwargs)

    async def ainfer_branch(self, branching_call):
        """
        Invoked for a a() | b() branching call, this method determines
        which branch to explore and how its result should be inferred.
        """
        # 1. decide which branch to explore
        call: defer_call = random.choice(branching_call)
        
        # 2. check whether to re-sample branch or use cached result
        pass

        # 3. infer branch result
        target_node = self.qfct_to_node.get(query_function(call.target))
        return await self.ainfer(target_node, *call.args, **call.kwargs)

    async def ainfer(self, node, *args, **kwargs):
        """
        Infers the result of the given query node, assuming the 
        provided arguments and keyword arguments are the inputs.
        """
        # check if this is a sub-query call
        context = get_graph_context()

        # in new context, compute result and track inputs and outputs
        # as instance nodes and edges
        with InferenceCall(self, node) as call:
            result = await node.query_fct.__acall__(*args, **kwargs)
            
            # create corresponding instance graph structure
            instance_node = InstanceNode(result, call.inputs)
            # register new instance node in calling context (as input to calling query)
            if context is not None:
                context.inputs.append(instance_node)
            
            # track instance node in query node
            node.add_instance(instance_node)
            
            return result

    def infer(self, node, *args, **kwargs):
        return run_in_loop(self.ainfer(node, *args, **kwargs))

@dataclass
class InferenceCall:
    """
    Graph context for an graph inference call. 

    Allows call(...) and branch(...) calls to add edges between their
    results and the result of the current query call.
    """
    # inference graph we operate in
    graph: InferenceGraph
    # query node representing the current call
    node: "QueryNode"
    
    # inputs to the current call accumulated so far during
    # execution of the current query function
    inputs: list = field(default_factory=list)

    def __enter__(self):
        push_graph_context(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        pop_graph_context()


def _build_graph(query_fct, graph):
    """
    Constructs an LMQL inference graph from the call hierarchy 
    of the given query function.
    """
    query_node = QueryNode(query_fct.name, query_fct)
    
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