from dataclasses import dataclass, field
from lmql.graphs.nodes import *
from typing import Dict, Any
from lmql.graphs.runtime import push_graph_context, pop_graph_context

@dataclass
class InferenceCall:
    """
    Graph context for an graph inference call. 

    Allows call(...) and branch(...) calls to add edges between their
    results and the result of the current query call.
    """
    # inference graph we operate in
    graph: Any
    # query node representing the current call
    node: "QueryNode"
    
    # inputs to the current call accumulated so far during
    # execution of the current query function
    inputs: list = field(default_factory=list)
    
    # maps input values (id(value)) to the corresponding instance nodes
    inputs_mapping: Dict[int, InstanceNode] = field(default_factory=dict)
    # maps local value IDs (id(...)) to the corresponding scores
    value_scores: Dict[int, float] = field(default_factory=dict)
    
    # alternative deferred query call results for variables in the current call
    value_alternatives: Dict[int, list] = field(default_factory=dict)

    def __enter__(self):
        push_graph_context(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        pop_graph_context()