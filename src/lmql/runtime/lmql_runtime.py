import inspect
from dataclasses import dataclass
from typing import Any, Dict, Optional

from lmql.ops.ops import *
from lmql.runtime.output_writer import silent
from lmql.runtime.prompt_interpreter import PromptInterpreter, LMQLResult
from lmql.runtime.p2 import P2
from lmql.runtime.model_registry import LMQLModelRegistry
from lmql.runtime.postprocessing.conditional_prob import ConditionalDistributionPostprocessor
from lmql.runtime.postprocessing.group_by import GroupByPostprocessor
from lmql.runtime.langchain import LMQLChainMixIn

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
            return None
            # assert False, "Failed to resolve variable '" + name + "' in @lmql.query " + str(self.fct)

@dataclass
class FunctionContext:
    argnames: List[str]
    args_of_query: List[str]
    scope: LMQLInputVariableScope


class LMQLQueryFunction(LMQLChainMixIn):
    fct: Any
    output_variables: List[str]
    postprocessors: List[Any]
    scope: Any

    output_writer: Optional[Any] = None
    args: Optional[List[str]] = None
    model: Optional[Any] = None
    function_context: Optional[FunctionContext] = None

    is_langchain_use: bool = False
    
    def __init__(self, fct, output_variables, postprocessors, scope, *args, **kwargs):
        # check for pydantic base class and do kw initialization then
        if hasattr(self, "schema_json"):
            super().__init__(fct=fct, output_variables=output_variables, postprocessors=postprocessors, scope=scope, *args, **kwargs)
        else:
            # otherwise, do standard initialization
            self.fct = fct
            self.output_variables = output_variables
            self.postprocessors = postprocessors
            self.scope = scope
        
        self.output_writer = None
        self.args = [a for a in inspect.getfullargspec(fct).args if a != "context"]
        self.model = None
        # only set if the query is defined inline of a Python file
        self.function_context = None

    @property
    def input_keys(self) -> List[str]:
        self.is_langchain_use = True
        return self.args
    
    def __getattribute__(self, __name: str) -> Any:
        return super().__getattribute__(__name)

    @property
    def output_keys(self) -> List[str]:
        return self.output_variables

    def force_model(self, model):
        self.model = model

    def make_kwargs(self, *args, **kwargs):
        if self.function_context is None:
            return kwargs
        else:
            argnames = self.function_context.argnames
            args_of_query = self.function_context.args_of_query
            scope = self.function_context.scope

        assert len(args) == len(argnames), f"@lmql.query {self.fct.__name__} expects {len(argnames)} positional arguments, but got {len(args)}."
        captured_variables = set(args_of_query)
        for name, value in zip(argnames, args):
            if name in args_of_query:
                kwargs[name] = value
                captured_variables.remove(name)
    
        for v in captured_variables:
            kwargs[v] = scope.resolve(v)
        
        if "output_writer" in kwargs:
            self.output_writer = kwargs["output_writer"]
            del kwargs["output_writer"]
        else:
            self.output_writer = silent

        return kwargs

    def __call__(self, *args, **kwargs):
        if not self.is_langchain_use:
            return self.__acall__(*args, **kwargs)
        else:
            return super().__call__(*args, **kwargs)

    async def __acall__(self, *args, **kwargs):
        kwargs = self.make_kwargs(*args, **kwargs)

        interpreter = P2(force_model=self.model)
        if self.output_writer is not None:
            interpreter.output_writer = self.output_writer

        query_kwargs = {}
        for a in self.args:
            if a in kwargs.keys():
                query_kwargs[a] = kwargs[a]
            else:
                query_kwargs[a] = self.scope.resolve(a)
        
        # execute main prompt
        results = await interpreter.run(self.fct, **query_kwargs)

        # applies distribution postprocessor if required
        results = await (ConditionalDistributionPostprocessor(interpreter).process(results))

        # apply remaining postprocessors
        if self.postprocessors is not None:
            for postprocessor in self.postprocessors:
                results = await postprocessor.process(results, self.output_writer)
        
        interpreter.print_stats()

        return results

def context_call(fct_name, *args, **kwargs):
    return ("call:" + fct_name, args, kwargs)

def interrupt_call(fct_name, *args, **kwargs):
    return ("interrupt:" + fct_name, args, kwargs)

def tag(t):
    return f"<lmql:{t}/>"

def compiled_query(output_variables=None, group_by=None):
    if output_variables is None:
        output_variables = []
    
    postprocessors = []
    
    calling_frame = inspect.stack()[1]
    
    if group_by is not None:
        postprocessors.append(GroupByPostprocessor(group_by))
    
    # TODO validate that only one postprocessor is used

    def func_transformer(fct):
        return LMQLQueryFunction(fct, 
                                 output_variables=output_variables, 
                                 postprocessors=postprocessors, 
                                 scope=LMQLInputVariableScope(fct, calling_frame))
    return func_transformer
    