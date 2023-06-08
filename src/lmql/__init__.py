import lmql.version as version_info

"""
lmql.

A query language for language models.
"""

__version__ = version_info.version
__author__ = 'Luca Beurer-Kellner, Marc Fischer and Mark Mueller'
__email__ = "luca.beurer-kellner@inf.ethz.ch"
__license__ = "Apache 2.0"

import os
import tempfile

import lmql.runtime.lmql_runtime as lmql_runtime
import lmql.runtime.lmql_runtime as runtime_support
from lmql.utils.docstring_parser import *
from lmql.language.compiler import LMQLCompiler
# re-export lmql runtime functions
from lmql.runtime.lmql_runtime import (FunctionContext, LMQLInputVariableScope,
                                       LMQLQueryFunction, compiled_query, tag,
                                       EmptyVariableScope)
from lmql.runtime.model_registry import LMQLModelRegistry
from lmql.runtime.output_writer import headless, printing, silent, stream
from lmql.runtime.interpreter import LMQLResult
from lmql.models.model import model
from lmql.runtime.loop import main

model_registry = LMQLModelRegistry

def connect(server="http://localhost:8080", model_name="EleutherAI/gpt-j-6B"):
    print("warning: connect() is deprecated. Use set_backend() instead.")

def autoconnect():
    model_registry.autoconnect = True

def set_backend(backend):
    model_registry.backend_configuration = backend

def load(filepath=None, autoconnect=False, force_model=None, output_writer=None):
    if autoconnect: 
        model_registry.autoconnect = True
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

async def run_file(filepath, *args, output_writer=None, force_model=None, **kwargs):
    import inspect
    module = load(filepath, autoconnect=True, output_writer=output_writer, force_model=force_model)
    
    if module is None: 
        print("Failed to compile query.")
        return

    if output_writer is not None:
        module.query.output_writer = output_writer

    compiled_fct_args = module.query.args
    query_args = []

    calling_frame = inspect.stack()[1]
    scope = LMQLInputVariableScope(module.query.fct, calling_frame)
    for arg in compiled_fct_args:
        if scope.resolve(arg) == None:
            query_args.append(arg)

    output_variables = module.query.output_variables
    query_args = list(set(query_args) - set(output_variables))

    return await module.query(*args, **kwargs)

async def run(code, *args, **kwargs):
    """
    Compiles and runs the given query string asynchronously.

    For synchronous execution (w/o await), use `lmql.run_sync` instead.
    """
    q = _query_from_string(code)
    return await q(*args, **kwargs)
        
def run_sync(code, *args, **kwargs):
    """
    Compiles and runs the given query string synchronously.

    For async execution, use `lmql.run` instead.
    """
    q = _query_from_string(code, is_async=False)
    return q(*args, **kwargs)

def _query_from_string(s, input_variables=None, is_async=True):
    if input_variables is None: input_variables = []

    import inspect
    temp_lmql_file = tempfile.mktemp(suffix=".lmql")
    with open(temp_lmql_file, "w") as f:
        f.write(s)
    module = load(temp_lmql_file, autoconnect=True, output_writer=silent)
    
    # lmql.query(str) does not capture function context
    scope = EmptyVariableScope()
    compiled_query_fct_args = inspect.getfullargspec(module.query.fct).args
    fct_signature = inspect.Signature(parameters=[inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD) for name in input_variables])

    module.query.function_context = FunctionContext(fct_signature, compiled_query_fct_args, scope)
    module.query.is_async = is_async
    
    return module.query

def query(fct, input_variables=None, is_async=True):
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
    import inspect

    if type(fct) is LMQLQueryFunction: return fct

    # support for lmql.query(<query string>)
    if type(fct) is str: 
        return _query_from_string(fct, input_variables)
    else:
        assert input_variables is None, "input_variables must be None when using @lmql.query as a decorator."
    
    calling_frame = inspect.stack()[1]
    scope = LMQLInputVariableScope(fct, calling_frame)
    code = get_decorated_function_code(fct)

    temp_lmql_file = tempfile.mktemp(suffix=".lmql")
    with open(temp_lmql_file, "w") as f:
        f.write(code)
    module = load(temp_lmql_file, autoconnect=True, output_writer=silent)
    
    is_async = inspect.iscoroutinefunction(fct)
    
    decorate_fct_signature = inspect.signature(fct)
    compiled_query_fct_args = inspect.getfullargspec(module.query.fct).args
    
    # set the function context of the query based on the function context of the decorated function
    module.query.function_context = FunctionContext(decorate_fct_signature, compiled_query_fct_args, scope)
    module.query.is_async = is_async

    def lmql_query_wrapper(*args, **kwargs):
        return module.query(*args, **kwargs)

    # copy all attributes of model.query to the wrapper function
    for attr in ["aschain"]:
        setattr(lmql_query_wrapper, attr, getattr(module.query, attr))

    return lmql_query_wrapper

async def static_prompt(query_fct, *args, **kwargs):
    """
    Returns the static prompt prefix that is generated by the given query function up until the first variable.
    """
    res = await query_fct(*args, **kwargs, return_prompt_string=True)
    return res[0]

def serve(*args, **kwargs):
    assert not "LMQL_BROWSER" in os.environ, "lmql.serve is not available in the browser distribution of LMQL."
    from lmql.models.lmtp.lmtp_serve import serve
    return serve(*args, **kwargs)
