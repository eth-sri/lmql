import lmql.version as version_info

"""
lmql.

A query language for language models.
"""

__version__ = version_info.version
__author__ = 'Luca Beurer-Kellner, Marc Fischer and Mark Mueller'
__email__ = "luca.beurer-kellner@inf.ethz.ch"
__license__ = "MIT"

import os
import tempfile

import lmql.runtime.lmql_runtime as lmql_runtime
import lmql.runtime.lmql_runtime as runtime_support
from lmql.language.compiler import LMQLCompiler
# re-export lmql runtime functions
from lmql.runtime.lmql_runtime import (FunctionContext, LMQLInputVariableScope,
                                       LMQLQueryFunction, compiled_query, tag)
from lmql.runtime.model_registry import LMQLModelRegistry
from lmql.runtime.output_writer import headless, printing, silent, stream
from lmql.runtime.interpreter import LMQLResult

model_registry = LMQLModelRegistry

def connect(server="http://localhost:8080", model_name="EleutherAI/gpt-j-6B"):
    from lmql.runtime.hf_integration import transformers_model

    Model = transformers_model(server, model_name)
    lmql_runtime.register_model(model_name, Model)
    lmql_runtime.register_model("*", Model)

def _autoconnect_model(model_name):
    if model_name.startswith("openai/"):
        from lmql.runtime.openai_integration import openai_model

        # hard-code openai/ namespace to be openai-API-based
        Model = openai_model(model_name[7:])
        lmql_runtime.register_model(model_name, Model)
        lmql_runtime.register_model("*", Model)
    else:
        if "LMQL_BROWSER" in os.environ:
            assert False, "Cannot use HuggingFace Transformers models in browser. Please use openai/ models or install lmql on your local machine."

        from lmql.runtime.hf_integration import transformers_model

        default_server = "http://localhost:8080"
        Model = transformers_model(default_server, model_name)
        lmql_runtime.register_model(model_name, Model)
        lmql_runtime.register_model("*", Model)

def make_pinned_model(model_name):
    _autoconnect_model(model_name)
    return model_registry.get(model_name)

def autoconnect():
    model_registry.autoconnect = _autoconnect_model

def load(filepath=None, autoconnect=False, force_model=None, output_writer=None):
    if autoconnect: 
        model_registry.autoconnect = _autoconnect_model
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

    if len(args) > 0:
        assert False, "Positional arguments for queries are not supported yet"
    else:
        assert len(kwargs) == len(query_args), f"Expected {len(query_args)} keyword arguments for query, got {len(kwargs)}"

        for query_kw in kwargs.keys():
            assert query_kw in query_args, f"Unknown query argument '{query_kw}'"
            
    return await module.query(**kwargs)

async def run(code, *args, output_writer=None, **kwargs):
    temp_lmql_file = tempfile.mktemp(suffix=".lmql")
    with open(temp_lmql_file, "w") as f:
        f.write(code)
    
    os.chdir(os.path.join(os.path.dirname(__file__), "../../")) 
    return await run_file(temp_lmql_file, *args, output_writer=output_writer, **kwargs)
        
def _query_from_string(s):
    temp_lmql_file = tempfile.mktemp(suffix=".lmql")
    with open(temp_lmql_file, "w") as f:
        f.write(s)
    module = load(temp_lmql_file, autoconnect=True, output_writer=silent)
    return module.query
        
def _get_decorated_function_code(fct):
    import ast
    import inspect

    source = ""

    try:
        source = inspect.getsource(fct)
        tree = ast.parse(source)
        docstring_element = tree.body[0].body[0].value
        docstring = docstring_element.s
        # get range of source that corresonds to the docstring
        start = docstring_element.lineno
        end = docstring_element.end_lineno
        startcol = docstring_element.col_offset
        endcol = docstring_element.end_col_offset
        
        # get source code of the function
        source = source.splitlines()

        # remove common indent
        common_indent = None
        lines = []
        for line in source[start-1:end]:
            if line.strip() == "" or line.strip() == '"""lmql' or line.strip() == "'''lmql":
                lines.append(line)
                continue
            if common_indent is None:
                common_indent = len(line) - len(line.lstrip())
            else:
                common_indent = min(common_indent, len(line) - len(line.lstrip()))
            lines.append(line[common_indent:])
        lines[0] = lines[0][startcol - common_indent:]
        lines[-1] = lines[-1][:endcol]

        source = "\n".join(lines)

        quote_types = "'''" if source.endswith("'''") else '"""'
        if source.lstrip().startswith(quote_types):
            source = source.lstrip()[len(quote_types):]
        assert source.endswith(quote_types), f"Docstring of @lmql.query function {fct.__name__} must be on the first line of the function, but is:\n {source}"
        source = source[:-len(quote_types)].strip("\n")
    except:
        raise RuntimeError("Failed to parse docstring of query function as LMQL code:\n\n" + str(source))

    return source


def query(fct):
    import inspect

    # support for lmql.query(<query string>)
    if type(fct) is str: return _query_from_string(fct)
    
    calling_frame = inspect.stack()[1]
    scope = LMQLInputVariableScope(fct, calling_frame)
    code = _get_decorated_function_code(fct)

    temp_lmql_file = tempfile.mktemp(suffix=".lmql")
    with open(temp_lmql_file, "w") as f:
        f.write(code)
    module = load(temp_lmql_file, autoconnect=True, output_writer=silent)
    
    assert inspect.iscoroutinefunction(fct), f"@lmql.query {fct.__name__} must be declared async."
    
    argnames = inspect.getfullargspec(fct).args
    
    args_of_query = [a for a in inspect.getfullargspec(module.query.fct).args if a != "context"]
    # print code of module.query.fct
    for a in argnames:
        if a not in args_of_query:
            print(f"warning: @lmql.query {fct.__name__} has an argument '{a}' that is not used in the query.")
    
    # set the function context of the query based on the function context of the decorated function
    module.query.function_context = FunctionContext(argnames, args_of_query, scope)
    
    return module.query

async def static_prompt(query_fct, *args, **kwargs):
    """
    Returns the static prompt prefix that is generated by the given query function up until the first variable.
    """
    res = await query_fct(*args, **kwargs, return_prompt_string=True)
    return res[0]
