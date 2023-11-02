from .nodes import *
from .runtime import call, defer_call, branch, annotate_score, scorer, checkpoint
from lmql.graphs.graph import InferenceGraph, query_function, InferenceCall, identity
from .solvers import Sampling

def infer(fct, *args, samples=1, parallel=1, state=None, enumerative=False, solver=None, **kwargs):
    """
    Use the LMQL graph execution engine to infer the result of a 
    graph of LMQL query functions.
    """
    solver = solver or Sampling()

    qfct = query_function(fct)
    graph, qnode = InferenceGraph.from_query(qfct)
    
    with open(state, "w") as f:
        f.write(graph.to_json())
    
    def save():
        with open(state, "w") as f:
            f.write(graph.to_json())
    graph.on_infer = save

    results = []

    for _ in range(samples):
        results += solver.step(graph, qnode, *args, parallel=parallel, **kwargs)
        save()
    
    return results