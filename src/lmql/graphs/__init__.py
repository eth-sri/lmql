from .nodes import *
from .runtime import call, defer_call, branch, annotate_score, scorer, checkpoint
from lmql.graphs.graph import InferenceGraph, query_function, InferenceCall, identity

def infer(fct, *args, samples=1, state=None, enumerative=False, **kwargs):
    """
    Use the LMQL graph execution engine to infer the result of a 
    graph of LMQL query functions.
    """
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
        with InferenceCall(graph, qnode, args, kwargs) as call:
            results += [graph.infer(qnode, *args, **kwargs)]

        if enumerative:
            for i in qnode.dangling():
                print("dangling result", graph.complete(i))
                save()
        save()
    
    return results