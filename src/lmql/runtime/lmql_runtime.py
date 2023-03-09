from dataclasses import dataclass
from typing import Any, Dict

from lmql.ops.ops import *
from lmql.runtime.prompt_interpreter import PromptInterpreter, LMQLResult
from lmql.runtime.model_registry import LMQLModelRegistry
from lmql.runtime.postprocessing.conditional_prob import ConditionalDistributionPostprocessor
from lmql.runtime.postprocessing.group_by import GroupByPostprocessor

def register_model(identifier, ModelClass):
    LMQLModelRegistry.registry[identifier] = ModelClass

class LMQLQueryFunction:
    def __init__(self, fct, postprocessors):
        self.output_writer = None
        self.fct = fct
        self.postprocessors = postprocessors

        self.model = None

    def force_model(self, model):
        self.model = model

    async def __call__(self, *args, **kwargs):
        interpreter = PromptInterpreter(force_model=self.model)
        if self.output_writer is not None:
            interpreter.output_writer = self.output_writer
        
        # execute main prompt
        results = await interpreter.run(self.fct, *args, **kwargs)

        # applies distribution postprocessor if required
        results = await (ConditionalDistributionPostprocessor(interpreter).process(results))

        # apply remaining postprocessors
        if self.postprocessors is not None:
            for postprocessor in self.postprocessors:
                results = await postprocessor.process(results, self.output_writer)
        
        interpreter.print_stats()

        return results

def query(group_by=None):
    postprocessors = []
    
    if group_by is not None:
        postprocessors.append(GroupByPostprocessor(group_by))
    
    # TODO validate that only one postprocessor is used

    def func_transformer(fct):
        return LMQLQueryFunction(fct, postprocessors=postprocessors)
    return func_transformer