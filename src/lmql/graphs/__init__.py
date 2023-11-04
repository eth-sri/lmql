from .nodes import *
from .runtime import call, defer_call, branch, annotate_score, scorer, checkpoint
from lmql.graphs.graph import InferenceGraph, query_function, InferenceCall, identity
from .solvers import Sampling, get_default_solver
from lmql.runtime.loop import run_in_loop

def num_samples():
    import sys
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except:
            return 2
    return 2

def infer(fct, *args, samples=None, parallel=1, state=None, enumerative=False, solver=None, **kwargs):
    return run_in_loop(ainfer(fct=fct, *args, samples=samples, parallel=parallel, state=state, enumerative=enumerative, solver=solver, **kwargs))

async def ainfer(fct, *args, samples=None, parallel=1, state=None, enumerative=False, solver=None, **kwargs):
    """
    Use the LMQL graph execution engine to infer the result of a 
    graph of LMQL query functions.
    """
    solver = solver or get_default_solver()
    
    samples = samples or num_samples()

    qfct = query_function(fct)
    graph, qnode = InferenceGraph.from_query(qfct)
    
    if state is not None:
        with open(state, "w") as f:
            f.write(graph.to_json())
    
    def save():
        if state is not None:
            with open(state, "w") as f:
                f.write(graph.to_json())
    graph.on_infer = save

    results = await solver.ainfer(graph, qnode, *args, samples=samples, parallel=parallel, **kwargs)
    save()
    return graph