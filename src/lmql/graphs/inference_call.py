from dataclasses import dataclass, field
from lmql.graphs.nodes import *
from typing import Dict, Any, Tuple, Optional
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
    # the solver used for graph inference
    solver: "Solver"
    
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    
    # inputs to the current call accumulated so far during
    # execution of the current query function
    inputs: list = field(default_factory=list)
    
    # maps input values (id(value)) to the corresponding instance nodes
    inputs_mapping: Dict[int, InstanceNode] = field(default_factory=dict)
    # maps local value IDs (id(...)) to the corresponding scores
    value_scores: Dict[int, float] = field(default_factory=dict)
    
    # alternative branched query executions
    dangling_nodes: List[InstanceNode] = field(default_factory=list)

    dangling_created: bool = False

    # indicates root 'solver' call
    root: bool = False

    def __enter__(self):
        push_graph_context(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        pop_graph_context()

    def score(self, value):
        score = 1.0
        if result_node := self.inputs_mapping.get(id(value)):
            score = result_node.score

        # otherwise check if result has been manually annotated with 
        # a score (e.g. a@0.1)
        elif value_score := self.value_scores.get(id(value)):
            score = value_score

        return score