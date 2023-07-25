"""
Runtime support used by compiled LMQL query code.
"""

import inspect
from dataclasses import dataclass
from typing import Any, Dict, Optional

from lmql.ops.ops import *
from lmql.runtime.langchain import chain, call_sync
from lmql.runtime.output_writer import silent
from lmql.runtime.interpreter import PromptInterpreter
from lmql.runtime.postprocessing.conditional_prob import \
    ConditionalDistributionPostprocessor
from lmql.runtime.postprocessing.group_by import GroupByPostprocessor

class LMQLInputVariableScope:
    def __init__(self, f, calling_frame):
        self.fct = f
        
        self.builtins = __builtins__
        self.globals =  calling_frame.frame.f_globals
        self.locals = calling_frame.frame.f_locals
    
    def resolve(self, name, errors=None):
        if name in self.locals.keys():
            return self.locals[name]
        elif name in self.globals.keys():
            return self.globals[name]
        elif name in self.builtins.keys():
            return self.builtins[name]
        else:
            if errors == "ignore":
                return None
            else:
                raise TypeError("Failed to resolve value of variable '" + name + "' in @lmql.query " + str(self.fct), name)

class EmptyVariableScope:
    def resolve(self, name, errors=None):
        if name in __builtins__.keys():
            return __builtins__[name]
        else:
            if errors == "ignore":
                return None
            else:
                raise TypeError("Failed to resolve value of variable '" + name + "' in @lmql.query function.")

@dataclass
class FunctionContext:
    argnames: inspect.Signature
    args_of_query: List[str]
    scope: LMQLInputVariableScope


class LMQLQueryFunction:
    fct: Any
    output_variables: List[str]
    postprocessors: List[Any]
    scope: Any

    name: str = None

    output_writer: Optional[Any] = None
    args: Optional[List[str]] = None
    model: Optional[Any] = None
    function_context: Optional[FunctionContext] = None
    
    # extra arguments to consider as query context (e.g. passed to the @lmql.query(<args>) decorator)
    extra_args: Dict = None

    lmql_code: str = None

    __lmql_query_function__ = True
    is_async: bool = True
    
    def __init__(self, fct, output_variables, postprocessors, scope, *args, **kwargs):
        self.fct = fct
        self.output_variables = output_variables
        self.postprocessors = postprocessors
        self.scope = scope
        
        self.output_writer = None
        self.args = [a for a in inspect.getfullargspec(fct).args if a != "context"]
        self.model = None
        # only set if the query is defined inline of a Python file
        self.function_context = None

    def __hash__(self):
        return hash(self.fct)

    @property
    def input_keys(self) -> List[str]:
        return self.args
    
    def __getattribute__(self, __name: str) -> Any:
        return super().__getattribute__(__name)

    @property
    def output_keys(self) -> List[str]:
        return self.output_variables

    def force_model(self, model):
        self.model = model

    def try_bind_positional_to_kwargs(self, signature, *args, **query_kwargs):
        """
        Best-effort attempt to bind positional arguments to keyword arguments in order of self.args. 

        Only enabled for lmql.F for now, may have unexpected effects depending on the order query
        arguments as determined by the compiler.
        """
        # only bind if kwargs are empty and no signature is provided (lmql.F or lmql.run)
        if len(signature.parameters) != 0 or len(self.args) != len(args):
            return
        kwargs = {**{k:v for k,v in zip(self.args, args)}, **query_kwargs}

        return inspect.BoundArguments(
            signature=inspect.Signature(parameters=[inspect.Parameter(name=k, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD) for k in self.args]),
            arguments=kwargs
        )

    def make_kwargs(self, *args, **kwargs):
        """
        Binds args and kwargs to the function signature and returns a dict of all user-defined kwargs.

        Resolves additional captured variables using the surrounding function context.
        """
        assert self.function_context is not None, "Cannot call @lmql.query function without context."
        
        signature = self.function_context.argnames
        args_of_query = self.function_context.args_of_query
        scope = self.function_context.scope
        
        runtime_args = {k:v for k,v in kwargs.items() if not k in signature.parameters.keys() and k not in args_of_query}
        query_kwargs = {k:v for k,v in kwargs.items() if k in signature.parameters.keys()}

        compiled_query_args = {}

        # initialize with default values
        for name, param in signature.parameters.items():
            if param.default is not inspect.Parameter.empty and name in args_of_query:
                compiled_query_args[name] = param.default

        # bind args and kwargs to signature
        try:
            signature: inspect.BoundArguments = signature.bind(*args, **query_kwargs)
        except TypeError as e:
            if "too many positional arguments" in str(e):
                # this is different from Python behavior, but we allow it for lmql.F and lmql.run
                pos_as_kw = self.try_bind_positional_to_kwargs(signature, *args, **kwargs)
                if pos_as_kw is not None:
                    signature = pos_as_kw
                else:
                    raise e
            else:    
                if len(e.args) == 1 and e.args[0].startswith("missing "):
                    e.args = (f"Call to @lmql.query function is " + e.args[0] + "." + f" Expecting {signature}, but got positional args {args} and {kwargs}.",)
                elif len(e.args) == 1:
                    e.args = (e.args[0] + "." + f" Expecting {signature}, but got positional args {args} and {kwargs}.",)
                raise e
        
        signature.apply_defaults()

        # special case, if signature is empty (no input variables provided)
        if len(signature.arguments) == 0:
            # bind kwargs dynamically in compiled_query_args
            for k,v in kwargs.items():
                if k in args_of_query:
                    # compiled_query_args[k] = v
                    compiled_query_args[k] = v
                else:
                    runtime_args[k] = v

        # resolve remaining variables from function context
        captured_variables = set(args_of_query)
        for name, value in signature.arguments.items():
            if name in args_of_query:
                compiled_query_args[name] = value
                captured_variables.remove(name)

        failed_to_resolve = []

        # resolve remaining unset args from scope
        for v in captured_variables:
            if not v in compiled_query_args:
                try:
                    compiled_query_args[v] = scope.resolve(v, errors="raise")
                except TypeError:
                    failed_to_resolve.append(v)

        # disable this check for now, as dynamic variable resolution cannot always be checked at compile time (e.g. import * from module)
        if len(failed_to_resolve) == 1:
            raise TypeError("Failed to resolve variable '" + failed_to_resolve[0] + "' in LMQL query.")
        elif len(failed_to_resolve) > 0:
            raise TypeError("Failed to resolve variables in LMQL query: " + ", ".join(f"'{v}'" for v in sorted(failed_to_resolve)))

        return compiled_query_args, runtime_args

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if not self.is_async:
            return call_sync(self, *args, **kwargs)

        return self.__acall__(*args, **kwargs)

    async def __acall__(self, *args, **kwargs):
        query_kwargs, runtime_args = self.make_kwargs(*args, **kwargs)
        
        forced_model = self.model or runtime_args.get("model") or (self.extra_args or {}).get("model")
        interpreter = PromptInterpreter(force_model=forced_model)

        if self.output_writer is not None:
            runtime_args["output_writer"] = self.output_writer
        runtime_args  = {**(self.extra_args or {}), **runtime_args}
        interpreter.set_extra_args(**runtime_args)

        # rename 'self'
        if "self" in query_kwargs:
            query_kwargs["__self__"] = query_kwargs.pop("self")

        # keep track of the main interpreter (only produces debug output for this one)
        try:
            if PromptInterpreter.main is None:
                PromptInterpreter.main = interpreter
            # execute main prompt
            results = await interpreter.run(self.fct, **query_kwargs)
        finally:
            if PromptInterpreter.main == interpreter:
                PromptInterpreter.main = None

        # applies distribution postprocessor if required
        results = await (ConditionalDistributionPostprocessor(interpreter).process(results))

        # apply remaining postprocessors
        if self.postprocessors is not None:
            for postprocessor in self.postprocessors:
                results = await postprocessor.process(results, self.output_writer)
        
        interpreter.print_stats()
        interpreter.dcmodel.close()

        # for lmql.F we assume 'argmax' and unpack the result
        if "is_f_function" in interpreter.extra_kwargs:
            results = results[0]

        return results

    def aschain(self, output_keys=None):
        """
        Returns a LangChain 'Chain' object that can be used to chain multiple queries together.

        Args:
            output_keys: List of output keys in LangChain. If None, output keys are automatically derived from 
                the set of template variables in the query.
        """
        return chain(self, output_keys=output_keys)

def context_call(fct_name, *args, **kwargs):
    return ("call:" + fct_name, args, kwargs)

def interrupt_call(fct_name, *args, **kwargs):
    return ("interrupt:" + fct_name, args, kwargs)

def f_escape(s):
    return str(s).replace("[", "[[").replace("]", "]]")

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
    

async def call(fct, *args, **kwargs):
    if type(fct) is LMQLQueryFunction or (hasattr(fct, "__lmql_query_function__") and fct.__lmql_query_function__.is_async):
        result = await fct(*args, **kwargs)
        if len(result) == 1: 
            return result[0]
        else: 
            return result
    if inspect.iscoroutinefunction(fct):
        return await fct(*args, **kwargs)
    else:
        return fct(*args, **kwargs)