import os
import tempfile

import lmql.runtime.lmql_runtime as lmql_runtime
import lmql.runtime.lmql_runtime as runtime_support
from .inspect import is_query

from lmql.utils.docstring_parser import *
from lmql.language.compiler import LMQLCompiler
# re-export lmql runtime functions
from lmql.runtime.lmql_runtime import (FunctionContext, LMQLInputVariableScope,
                                       LMQLQueryFunction, compiled_query, tag,
                                       EmptyVariableScope)
from lmql.runtime.output_writer import headless, printing, silent, stream

from typing import Optional, Union
from functools import wraps
    
def load(filepath=None, force_model=None, output_writer=None):
    # compile query and obtain the where clause computational graph
    compiler = LMQLCompiler()
    module = compiler.compile(filepath)
    if module is None: 
        return None
    
    if output_writer is not None:
        output_writer.add_compiler_output(module.code())

    module = module.load()
    module.query.force_model(force_model)
    return module

def query_from_string(s, input_variables=None, is_async=True, output_writer=None, **extra_args):
    if input_variables is None: input_variables = []

    import inspect
    temp_lmql_file = tempfile.mktemp(suffix=".lmql")
    with open(temp_lmql_file, "w", encoding="utf-8") as f:
        f.write(s)
    module = load(temp_lmql_file, output_writer=output_writer or silent)
    
    # lmql.query(str) does not capture function context
    scope = EmptyVariableScope()
    compiled_query_fct_args = inspect.getfullargspec(module.query.fct).args
    fct_signature = inspect.Signature(parameters=[inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD) for name in input_variables])

    module.query.function_context = FunctionContext(fct_signature, compiled_query_fct_args, scope)
    module.query.is_async = is_async
    module.query.output_writer = output_writer
    module.query.extra_args = extra_args
    
    return module.query

def F(s: str, constraints: Optional[str] = None, **kwargs):
    """
    Constructs a LMQL query function from the given string.

    Example:

    ```python
    lmql.F("Say 'this is a test': [RESPONSE]", "len(TOKENS(RESPONSE)) < 10")
    ```

    The second argument contains an optional `where` clause expression and can be omitted.

    The resulting callable acts like a `lmql.query` function and can be called with the same arguments.
    """
    # escape all double quotes
    s = s.replace('"', '\\"')
    is_async = kwargs.pop("is_async", False)
    return query(f'"{s}"' + (f' where {constraints}' if constraints is not None else ''), is_async=is_async, is_f_function=True, **kwargs)

def query(__fct__=None, input_variables=None, is_async=True, calling_frame=None, **extra_args):
    """
    Constructs a new LMQL query function from the given function and or string of code.

    You can use `lmql.query` as a function decorator or to compile a string of LMQL code.

    * As a decorator, it can be used as follows:

        ```python
        @lmql.query
        def my_query_function():
            '''
            <LMQL codee>
            '''
        ```

        @lmql.query functions can also be annotated as async, in which case the returned query function will be async as well.

    * As an alternative @lmql.query, you can also pass a string of LMQL code to `lmql.query` directly:

        ```python
        my_query_function = lmql.query('''
            <LMQL code>
        ''')

        By default the returned query function is asynchronous (has to be called as `await my_query_function(...)`).
        To construct a synchronous query function, use lmql.query(<query string>, is_async=False).
    """
    fct = __fct__

    # check for @lmql.query(<args>) def f(): ... use with additional arguments
    if fct is None:
        def wrapper(fct):
            import inspect
            calling_frame = inspect.stack()[1]
            return query(fct, input_variables=input_variables, is_async=is_async, calling_frame=calling_frame, **extra_args)
        return wrapper

    # otherwise assume @lmql.query def f(): ...
    import inspect

    if type(fct) is LMQLQueryFunction: return fct

    # support for lmql.query(<query string>)
    if type(fct) is str: 
        return query_from_string(fct, input_variables, is_async=is_async, **extra_args)
    else:
        assert input_variables is None, "input_variables must be None when using @lmql.query as a decorator."
    
    calling_frame = calling_frame or inspect.stack()[1]
    scope = LMQLInputVariableScope(fct, calling_frame)
    code = get_decorated_function_code(fct)

    # compile query and load it into this python process
    temp_lmql_file = tempfile.mktemp(suffix=".lmql")
    with open(temp_lmql_file, "w") as f:
        f.write(code)
    module = load(temp_lmql_file, output_writer=silent)

    # get function signature
    is_async = inspect.iscoroutinefunction(fct)
    decorated_fct_signature = inspect.signature(fct)
    
    compiled_query_fct_args = inspect.getfullargspec(module.query.fct).args
    
    # set the function context of the query based on the function context of the decorated function
    module.query.function_context = FunctionContext(decorated_fct_signature, compiled_query_fct_args, scope)
    module.query.is_async = is_async
    module.query.extra_args = extra_args

    # name the query function after the decorated function
    module.query.name = fct.__name__

    @wraps(fct)
    def lmql_query_wrapper(*args, **kwargs):
        return module.query(*args, **kwargs)

    # copy some attributes of model.query to the wrapper function
    for attr in ["aschain", "lmql_code", "is_async", "output_variables"]:
        setattr(lmql_query_wrapper, attr, getattr(module.query, attr))
    setattr(lmql_query_wrapper, "__lmql_query_function__", module.query)

    return lmql_query_wrapper

async def static_prompt(query_fct, *args, **kwargs):
    """
    Returns the static prompt prefix that is generated by the given query function up until the first variable.
    """
    res = await query_fct(*args, **kwargs, return_prompt_string=True)
    return res[0]
