from typing import List

from lmql.graphs.nodes import InstanceNode, List
from .nodes import *
from abc import ABC, abstractmethod
import random
import asyncio
from .inference_call import InferenceCall
from .runtime import defer_call
from .nodes import *
from lmql.runtime.loop import run_in_loop

class Solver(ABC):
    """
    Base class for solvers.
    """
    def __init__(self):
        pass

    @abstractmethod
    def choice(self, candidates: List[InstanceNode], call: InferenceCall):
        """
        Returns the next candidate 'InstanceNode' to sample a result for.

        Can raise a 'StopIteration' exception to signal that the solver can stop inference at 
        this point, due to solver-specific termination criteria (e.g. threshold reached, etc.).
        """
        pass

    def infer(self, graph, qnode, *args, samples=1, parallel=1, **kwargs):
        return run_in_loop(self.ainfer(graph, qnode, *args, samples=samples, parallel=parallel, **kwargs))

    async def ainfer(self, graph, qnode, *args, samples=1, parallel=1, **kwargs):
        """
        Infers a result for 'qnode' in 'graph' and returns it.

        Uses at most 'samples' many graph samples with a step width of 'parallel'.
        """
        results = []
        for i in range(samples):
            try:
                results += await self.astep(graph, qnode, *args, parallel=parallel, **kwargs)
            except RuntimeError as e:
                if "StopIteration" in str(e):
                    print(str(self), "stopping early after", i, "samples.")
                    break
                else:
                    raise e
        return results

    async def do_step(self, graph, qnode, *args, **kwargs):
        """
        Samples a single result for 'qnode' in 'graph' and returns it.

        Stores any arising state and dangling paths in 'graph'.
        """
        candidates = [inode for inode in qnode.instances if inode.dangling] + \
                     [InstanceNode.candidate(qnode, defer_call(qnode.query_fct, *args, **kwargs))]

        with InferenceCall(graph, qnode, self, args, kwargs, root=True) as call:
            # select next candidate
            call_node = self.choice(candidates, call)
            
            # check if we need an inference call (fresh samples) or 
            # partially completed inference call (dangling paths)
            if call_node.dangling:
                return await graph.acomplete(call_node, self)
            else:
                return await graph.ainfer(qnode, *args, **kwargs)

    def step(self, graph, qnode, *args, parallel=1, **kwargs):
        """
        (See astep.)
        """
        return run_in_loop(self.astep(graph, qnode, *args, parallel=parallel, **kwargs))

    async def astep(self, graph, qnode, *args, parallel=1, **kwargs):
        """
        Performs a solver step for 'qnode' in 'graph' and returns the results.

        :param graph: the inference graph to operate on.
        :param qnode: the query node to sample results for.
        :param *args and **kwargs: passed to the inference graph's entry point query function.
        :param parallel: number of parallel inference calls to perform in this step (step width).
        
        """
        results = []
        try:
            tasks = await asyncio.gather(*[self.do_step(graph, qnode, *args, **kwargs) for _ in range(parallel)])
            for t in tasks:
                results += [t]
        except RuntimeError as e:
            if "StopIteration" in str(e):
                raise StopIteration("Solver can stop inference at this point.")
            else:
                raise e
        return results

class Sampling(Solver):
    """
    Samples all branching points (including root calls) randomly with equal probability.

    :param include_dangling: if False, only non-dangling candidates are considered for root calls.
    """
    def __init__(self, include_dangling=True):
        self.include_dangling = include_dangling

    def choice(self, candidates: List[InstanceNode], call: InferenceCall):
        if call.root and not self.include_dangling:
            candidates = [c for c in candidates if not c.dangling]
            assert len(candidates) > 0, "No non-dangling candidates found for root call. This indicates a bug in the inference engine."
        return random.choice(candidates)

    def __repr__(self):
        return f"<Sampling solver include_dangling={self.include_dangling}>"
class ExploreAll(Solver):
    """
    Explores all dangling root paths, before sampling new paths. 

    Samples other branching points randomly with equal probability.
    """
    def __init__(self, early_stopping=True):
        self.early_stopping = early_stopping

    def can_stop(self, candidates: List, call: InferenceCall):
        if not self.early_stopping:
            return False

        if call.root:
            dangling = [c for c in candidates if c.dangling]
            non_dangling = [c for c in candidates if not c.dangling]
            return len(dangling) == 0 and len(non_dangling) == 1 and len(call.node.instances) > 0
        else:
            return False

    def choice(self, candidates: List[InstanceNode], call: InferenceCall):
        if call.root:
            dangling = [c for c in candidates if c.dangling]
            non_dangling = [c for c in candidates if not c.dangling]

            if self.can_stop(candidates, call):
                raise StopIteration("Solver can stop inference at this point.")

            return (dangling + non_dangling)[0]
        else:
            # return random.choice(candidates)
            
            # left depth first
            return candidates[0]
        
    def __repr__(self):
        return "<ExploreAll solver>"
        
def get_default_solver():
    # return ExploreAll(early_stopping=True)
    return Sampling(include_dangling=True)