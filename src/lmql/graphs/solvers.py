from typing import List
from .nodes import *
from abc import ABC, abstractmethod
import random
import asyncio
from .inference_call import InferenceCall
from .runtime import defer_call
from .nodes import *
from lmql.runtime.loop import run_in_loop

class Solver(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def choice(self, candidates: List[InstanceNode], call: InferenceCall):
        pass

    async def do_step(self, graph, qnode, *args, **kwargs):
        """
        Samples a single result for 'qnode' in 'graph' and returns it.

        Stores any arising state and dangling paths in 'graph'.
        """
        candidates = [inode for inode in qnode.instances if inode.dangling] + \
                     [InstanceNode.candidate(qnode, defer_call(qnode.query_fct, *args, **kwargs))]

        with InferenceCall(graph, qnode, self, args, kwargs, root=True) as call:
            call_node = self.choice(candidates, call)
            
            # check if we need an inference call (fresh samples) or 
            # partially completed inference call (dangling paths)
            if call_node.dangling:
                return await graph.acomplete(call_node, self)
            else:
                return await graph.ainfer(qnode, *args, **kwargs)

        # if enumerative:
        #     for i in qnode.dangling():
        #         print("dangling result", graph.complete(i))
        #         save()

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
        tasks = await asyncio.gather(*[self.do_step(graph, qnode, *args, **kwargs) for _ in range(parallel)])
        for t in tasks:
            results += t
        return results

class Sampling(Solver):
    def __init__(self, include_dangling=False):
        self.include_dangling = include_dangling

    def choice(self, candidates: List[InstanceNode], call: InferenceCall):
        if call.root and not self.include_dangling:
            candidates = [c for c in candidates if not c.dangling]
            assert len(candidates) > 0, "No non-dangling candidates found for root call. This indicates a bug in the inference engine."
        return random.choice(candidates)