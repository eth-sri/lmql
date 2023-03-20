import inspect
from dataclasses import dataclass
from typing import Any, Dict

from lmql.ops.ops import *
from lmql.runtime.prompt_interpreter import PromptInterpreter, LMQLResult
from lmql.runtime.model_registry import LMQLModelRegistry
from lmql.runtime.postprocessing.conditional_prob import ConditionalDistributionPostprocessor
from lmql.runtime.postprocessing.group_by import GroupByPostprocessor

def register_model(identifier, ModelClass):
    LMQLModelRegistry.registry[identifier] = ModelClass

class LMQLInputVariableScope:
    def __init__(self, f, calling_frame):
        self.fct = f
        
        self.builtins = __builtins__
        self.globals =  calling_frame.frame.f_globals
        self.locals = calling_frame.frame.f_locals
    
    def resolve(self, name):
        if name in self.locals.keys():
            return self.locals[name]
        elif name in self.globals.keys():
            return self.globals[name]
        elif name in self.builtins.keys():
            return self.builtins[name]
        else:
            assert False, "Failed to resolve variable '" + name + "' in @lmql.query " + str(self.fct)

class LMQLQueryFunction:
    def __init__(self, fct, postprocessors, scope):
        self.output_writer = None
        self.fct = fct
        self.postprocessors = postprocessors
        self.scope = scope
        self.args = [a for a in inspect.getfullargspec(fct).args if a != "context"]

        self.model = None

    def force_model(self, model):
        self.model = model

    async def __call__(self, *args, **kwargs):
        interpreter = PromptInterpreter(force_model=self.model)
        if self.output_writer is not None:
            interpreter.output_writer = self.output_writer

        query_kwargs = {}
        for a in self.args:
            if a in kwargs.keys():
                query_kwargs[a] = kwargs[a]
            else:
                query_kwargs[a] = self.scope.resolve(a)
        
        # execute main prompt
        results = await interpreter.run(self.fct, *args, **query_kwargs)

        # applies distribution postprocessor if required
        results = await (ConditionalDistributionPostprocessor(interpreter).process(results))

        # apply remaining postprocessors
        if self.postprocessors is not None:
            for postprocessor in self.postprocessors:
                results = await postprocessor.process(results, self.output_writer)
        
        interpreter.print_stats()

        return results

def tag(t):
    return f"<lmql:{t}/>"

def query(group_by=None):
    postprocessors = []
    
    calling_frame = inspect.stack()[1]
    
    if group_by is not None:
        postprocessors.append(GroupByPostprocessor(group_by))
    
    # TODO validate that only one postprocessor is used

    def func_transformer(fct):
        return LMQLQueryFunction(fct, postprocessors=postprocessors, scope=LMQLInputVariableScope(fct, calling_frame))
    return func_transformer