from typing import Any, Union, List, Optional, Dict
from abc import ABC, abstractmethod

from lmql.runtime.tokenizer import LMQLTokenizer
from lmql.runtime.tracing.tracer import traced
import lmql.runtime.dclib as dc
import os
from lmql.models.aliases import model_name_aliases
from lmql.runtime.loop import run_in_loop

from .queries import query
from .scoring import dc_score

import warnings

class ModelAPIAdapter(ABC):
    """
    Abstract base class for model API adapters (interface to integrate concrete
    model APIs with LMQL, e.g. LMTP or OpenAI/APIs directly).

    This class can be extended to implement new client-level inference backends, e.g.
    networking-only code that communicates with a remote model server. To implement
    lower-level backends that run models locally, including long running, blocking 
    code, please implement a corresponding LMTP backend instead, to benefit from efficient
    async I/O, parallelism and batching.

    All heavy/blocking initialization code should be deferred to the `get_dclib_model` method, 
    which is only called when the model is actually used for the first time. This allows users
    to instantiate lmql.model objects freely, without incurring any overhead until the
    model is actually used for the first time.
    """
    
    @abstractmethod
    def get_tokenizer(self) -> LMQLTokenizer:
        """
        Returns the tokenizer used by this model.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_dclib_model(self) -> dc.DcModel:
        """
        Returns the internal dclib.DcModel handle to actually use this model.

        This handle is used for token generation and decoding via its methods 
        like `argmax`, `sample` and `score`.

        If possible, only when calling this method, heavy, blocking initialization
        code should be executed, rather than in the constructor of the adapter.
        """
        raise NotImplementedError()

    @abstractmethod
    async def tokenize(self, text: str) -> Any:
        """
        Tokenizes the given text and returns the tokenized input_ids in
        the format expected by the model.
        """
        raise NotImplementedError()
    
    @abstractmethod
    async def detokenize(self, input_ids: Any) -> str:
        """
        Detokenizes the given input_ids and returns the detokenized text.
        """
        raise NotImplementedError()

class LLM:
    """
    An LMQL LLM is the core model object that is used to represent a language model and backend implementation.
    
    An LLM object can be used directly or passed to an LMQL query. For direct use,
    you can rely on the methods `generate` and `score` to generate text or score a list of
    potential continuations against a prompt.
    """

    def __init__(self, model_identifier: str, adapter: ModelAPIAdapter = None, configuration: Optional[Dict[str, Any]] = None):
        # identifier of the model, e.g. "openai/gpt-3.5-turbo-instruct"
        self.model_identifier = model_identifier
        # model configuration parameters passed when constructing this model
        self.configuration = configuration
        # adapter object that connects the LLM API to the backend
        self.adapter = adapter

    def get_tokenizer(self) -> LMQLTokenizer:
        """
        Returns the LMQLTokenizer to use for this model.
        """
        return self.adapter.get_tokenizer()

    async def generate(self, prompt, max_tokens=None, **kwargs):
        """
        Generates text from this model, given a simple prompt.

        Enforces a maximum number of tokens to be generated, if specified.
        
        All additional parameters in kwargs are passed to the underlying LMQL
        query program. For instance, you can specify `temperature=0.2` to generate
        text with a temperature of 0.2 or runtime parameters like `verbose=True`
        to OpenAI API request logging.
        """
        kwargs["model"] = self
        
        if max_tokens is not None:
            kwargs["chunksize"] = max_tokens
            max_tokens = max_tokens + 1
        
        name = "lmql.generate".format("...", max_tokens, kwargs)
        result = await generate_query(prompt, max_tokens=max_tokens, __name__=name, **kwargs)

        if len(result) == 0:
            raise ValueError("No result returned from query")
        if len(result) == 1:
            return result[0]
        else:
            return result

    def generate_sync(self, *args, **kwargs):
        """
        Syncronous version of `generate(...)`.

        If in an async context, use `await generate(...)` instead or
        make sure nested_asyncio is installed and enabled.
        """
        return run_in_loop(self.generate(*args, **kwargs))

    async def score(self, prompt: str, values: Union[str, List[str]], **kwargs):
        """
        Returns a ScoringResult object that contains the model scores for each 
        continuation in the given list of values, as an extension of the provided prompt.

        When inside an LMQL query, you can also use `context.score(...)` in the same way,
        to score a list of continuations against the prompt of the current query context.
        """
        try:
            dcmodel = self.adapter.get_dclib_model()
            with traced(str(self) + ".score"):
                with dc.Context(self.adapter.get_tokenizer(), dcmodel.truncation_threshold):
                    return await dc_score(dcmodel, prompt, values, **kwargs)
        finally:
            dcmodel.close()

    def score_sync(self, *args, **kwargs):
        """
        Syncronous version of `score(...)`.
        """
        return run_in_loop(self.score(*args, **kwargs))

    def __str__(self):
        configuration_string = ", ".join([f"{k}={v}" for k, v in self.configuration.items()])
        return f"lmql.LLM({self.model_identifier}, {configuration_string})"
    
    def __repr__(self):
        return str(self)

    @classmethod
    def from_descriptor(cls, model_identifier: Union[str, 'LLM'], **kwargs):
        """
        Constructs an LMQL model descriptor object to be used in 
        a `from` clause or as `model=<MODEL>` argument to @lmql.query(...).

        Alias for `lmql.model(...)`.
        """
        if model_identifier == "<dynamic>" or model_identifier is None:
            model_identifier = get_default_model()

        assert isinstance(model_identifier, (str, LLM)), "model_identifier must be a string or LLM object"

        # check for user-defined shorthands
        model_identifier = resolve_user_shorthands(cls, model_identifier)

        # do nothing if already a descriptor
        if type(model_identifier) is LLM:
            return model_identifier
        
        # check for built-in model name aliases
        if model_identifier in model_name_aliases:
            model_identifier = model_name_aliases[model_identifier]

        # remember original name
        original_name = model_identifier
        # to be copied to the LLM(...) object for reference
        configuration = kwargs.copy()

        # resolve default model
        if model_identifier == "<dynamic>":
            global default_model
            model_identifier = default_model
        
        endpoint = kwargs.pop("endpoint", None)

        if model_identifier.startswith("openai/"):
            from lmql.runtime.openai_integration import openai_model

            # hard-code openai/ namespace to be openai-API-based
            adapter = openai_model(model_identifier[7:], endpoint=endpoint, **kwargs)
            return cls(original_name, adapter=adapter, configuration=configuration)
        else:
            from lmql.models.lmtp.lmtp_dcmodel import lmtp_model
            from lmql.models.lmtp.lmtp_dcinprocess import inprocess

            # special case for 'random' model (see random_model.py)
            if model_identifier == "random":
                if "tokenizer" in kwargs:
                    kwargs["vocab"] = kwargs["tokenizer"]
                else:
                    kwargs["tokenizer"] = "gpt2"
                kwargs["inprocess"] = True
                kwargs["async_transport"] = True

            # special case for 'llama.cpp'
            if model_identifier.startswith("llama.cpp:"):
                if "tokenizer" in kwargs:
                    kwargs["tokenizer"] = kwargs["tokenizer"]
                else:
                    tokenizer_path = os.path.join(os.path.dirname(model_identifier.replace("llama.cpp:", "")), "tokenizer.model")
                    if os.path.exists(tokenizer_path):
                        kwargs["tokenizer"] = tokenizer_path
                    else:
                        warnings.warn("File tokenizer.model not present in the same folder as the model weights. Using default '{}' tokenizer for all llama.cpp models. To change this, set the 'tokenizer' argument of your lmql.model(...) object.".format("huggyllama/llama-7b", UserWarning))
                        kwargs["tokenizer"] = kwargs.get("tokenizer", "huggyllama/llama-7b")

            if model_identifier.startswith("replicate:"):
                model_identifier = model_identifier[10:]
                endpoint = "replicate:" + model_identifier

            # determine endpoint URL
            if endpoint is None:
                endpoint = "localhost:8080"

            # determine model name and if we run in-process
            if model_identifier.startswith("local:"):
                model_identifier = model_identifier[6:]
                kwargs["inprocess"] = True

            if kwargs.get("inprocess", False):
                Model = inprocess(model_identifier, use_existing_configuration=True, **kwargs)
            else:
                Model = lmtp_model(model_identifier, endpoint=endpoint, **kwargs)
            
            return cls(original_name, adapter=Model(), configuration=configuration)

"""
The default model for workloads or queries that do not specify 
a model explicitly.
"""
default_model = os.environ.get("LMQL_DEFAULT_MODEL", 
                               # otherwise use 'openai/gpt-3.5-turbo-instruct' (in browser, we use 
                               # openai/text-davinci-003, because 3.5 tokenizers are not supported in the browser)
                               "openai/gpt-3.5-turbo-instruct" if not "LMQL_BROWSER" in os.environ else "openai/text-davinci-003")

def get_default_model() -> Union[str, LLM]:
    """
    Returns the default model instance to be used when no 'from' clause or @lmql.query(model=<model>) are specified.

    This applies globally in the current process.
    """
    global default_model
    return default_model

def get_default_scoring_model() -> Union[str, LLM]:
    """
    Returns the default model instance to be used when no 'from' clause or @lmql.query(model=<model>) are specified and 
    the workload is a scoring workload.

    This applies globally in the current process.
    """
    global default_model
    if default_model == "openai/gpt-3.5-turbo-instruct":
        # we cannot use 3.5 instruct, because OpenAI blocks scoring for that model 
        # on an API level
        return "openai/text-davinci-003"
    return default_model

def set_default_model(model: Union[str, LLM]):
    """
    Sets the model instance to be used when no 'from' clause or @lmql.query(model=<model>) are specified.

    This applies globally in the current process.
    """
    global default_model
    default_model = model

def lazy_query(name):
    """
    Lazily initializes a lmql.query(...) function. This is useful for functions
    that should only be initialized once they are called for the first time.
    """
    def decorator(func):
        from functools import wraps
        query_func = None

        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal query_func
            if query_func is None:
                query_func = query(func)
            query_func.__lmql_query_function__.name = "lmql.generate"
            return query_func(*args, **kwargs)
        
        return wrapper
    return decorator

"""
Lazily initialized query to generate text from an LLM using the .generate(...) 
and .generate_sync(...) methods.
"""
@lazy_query("lmql.generate")
async def generate_query(prompt, max_tokens=32):
    '''lmql
    if max_tokens is not None:
        "{prompt}[RESPONSE]" where len(TOKENS(RESPONSE)) < max_tokens
    else:
        "{prompt}[RESPONSE]"
    return RESPONSE
    '''

def model(model_identifier, **kwargs) -> LLM:
    """
    Constructs a LLM model to be used in a `from` clause, as `model=<MODEL>` 
    argument to @lmql.query(...) or directly as `model.generate(...)`.

    Alias for `lmql.LLM.from_descriptor(...)`.

    Examples:

    lmql.model("openai/gpt-3.5-turbo-instruct") # OpenAI API model
    lmql.model("random", seed=123) # randomly sampling model
    lmql.model("llama.cpp:<YOUR_WEIGHTS>.bin") # llama.cpp model
    
    lmql.model("local:gpt2") # load a `transformers` model in process
    lmql.model("local:gpt2", cuda=True, load_in_4bit=True) # load a `transformers` model in process with additional arguments
    """
    from lmql.api.llm import LLM
    return LLM.from_descriptor(model_identifier, **kwargs)


def resolve_user_shorthands(self, model_name):
    """
    Resolves user-defined shorthands for model names.

    User-defined shorthands are stored in ~/.lmql/models and can be used to expand
    simple model identifiers to configured lmql.model(...) objects.

    For instance, you can define a shorthand like this:

    ```
    # ~/.lmql/models
    # this is a comment
    llama lmql.model("llama.cpp:/Users/luca/Developer/llama.cpp/models/7B/ggml-model-q4_0.bin")
    ```
    
    """
    # get ~/.cache/lmql/models file
    import os
    import ast

    if not os.path.exists(os.path.expanduser("~/.lmql/models")):
        return model_name

    try:
        with open(os.path.expanduser("~/.lmql/models"), "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.strip().startswith("#"):
                    continue
                shorthand, replacement = line.split(" ", 1)
                
                if model_name == shorthand or model_name == "local:" + shorthand:
                    # remember if we use the shorthand with local: prefix
                    is_local = model_name.startswith("local:")
                    
                    if replacement.startswith("lmql.model("):
                        # save lmql.model literal evaluation
                        parsed = ast.parse(replacement).body[0].value
                        args = ast.literal_eval(ast.unparse(parsed.args))
                        if len(parsed.args) == 1:
                            args = (args,)
                        kwargs = {k.arg: ast.literal_eval(ast.unparse(k.value)) for k in parsed.keywords}
                        kwargs["inprocess"] = is_local
                        return model(*args, **kwargs)
                    else:
                        if is_local:
                            replacement = "local:" + replacement
                        return replacement.rstrip()
    except Exception as e:
        warnings.warn("Failed to read ~/.lmql/models shorthand file.", UserWarning)

    return model_name
