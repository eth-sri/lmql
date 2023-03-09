"""
lmql.

A query language for language models.
"""

__version__ = "0.1.0"
__author__ = 'Luca Beurer-Kellner, Marc Fischer and Mark Mueller'
__email__ = "luca.beurer-kellner@inf.ethz.ch"
__license__ = "MIT"

from lmql.language.compiler import LMQLCompiler
import lmql.runtime.lmql_runtime as lmql_runtime
import tempfile
from lmql.runtime.prompt_interpreter import DebuggerOutputWriter
from lmql.runtime.model_registry import LMQLModelRegistry

import os

silent = DebuggerOutputWriter()
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
        Model = openai_model(model_name)
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

async def run_file(filepath, output_writer=None, force_model=None, *args):
    module = load(filepath, autoconnect=True, output_writer=output_writer, force_model=force_model)
    
    if module is None: 
        print("Failed to compile query.")
        return

    if output_writer is not None:
        module.query.output_writer = output_writer
    
    if len(args) == 1 and args[0] == "":
        kwargs = {}
    else:
        kwargs = {}
        for line in args:
            line = line.strip()
            key, value = line.split(":", 1)
            kwargs[key.strip()] = value.strip()

    return await module.query(**kwargs)

async def run(code, output_writer=None):
    print("run code", code)
    temp_lmql_file = tempfile.mktemp(suffix=".lmql")
    with open(temp_lmql_file, "w") as f:
        f.write(code)
    
    os.chdir(os.path.join(os.path.dirname(__file__), "../../"))
    return await run_file(temp_lmql_file, output_writer=output_writer)