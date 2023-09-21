from typing import Any, Union
from abc import ABC, abstractmethod

from lmql.runtime.tokenizer import LMQLTokenizer
import lmql.runtime.dclib as dc
from lmql.models.aliases import model_name_aliases

from .queries import query
from .scoring import dc_score
import warnings
import asyncio

class ModelAPIAdapter(ABC):
    """
    Abstract base class for model API adapters (interface to integrate concrete
    model APIs with LMQL, e.g. LMTP or OpenAI directly).

    This class can be extended to implement new client-space inference backends, e.g.
    networking-only code that communicates with a remote model server. To implement
    lower-level backends that run models locally, including long running, blocking 
    code, please implement a corresponding LMTP backend instead to benefit from efficient
    async I/O, parallelism and batching.
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
    An LMQL LLM is the core model object that is used to represent a specific
    language model. 
    
    An LLM object can be used directly or passed to an LMQL query. For direct use,
    consider the methods `generate` and `score` to generate text or score a list of
    potential continuations against a prompt.
    """

    def __init__(self, model_identifier: str, adapter: ModelAPIAdapter = None):
        self.model_identifier = model_identifier
        self.adapter = adapter

    def get_tokenizer(self) -> LMQLTokenizer:
        return self.adapter.get_tokenizer()

    async def generate(self, prompt, max_tokens=32, **kwargs):
        kwargs["model"] = self
        result = await get_generate_query()(prompt, max_tokens=max_tokens + 1, **kwargs)

        if len(result) == 0:
            raise ValueError("No result returned from query")
        if len(result) == 1:
            return result[0]
        else:
            return result

    def generate_sync(self, *args, **kwargs):
        return asyncio.run(self.generate(*args, **kwargs))

    def score(self, prompt, values, **kwargs):
        dcmodel = self.adapter.get_dclib_model()
        with dc.ContextTokenizer(self.adapter.get_tokenizer()):
            return dc_score(dcmodel, prompt, values, **kwargs)

    def __str__(self):
        return f"lmql.LLM({self.model_identifier})"
    
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

        # do nothing if already a descriptor
        if type(model_identifier) is LLM:
            return model_identifier
        
        # check for model name aliases
        if model_identifier in model_name_aliases:
            model_identifier = model_name_aliases[model_identifier]
        
        # remember original name
        original_name = model_identifier

        # resolve default model
        if model_identifier == "<dynamic>":
            global default_model
            model_identifier = default_model
        
        endpoint = kwargs.pop("endpoint", None)

        if model_identifier.startswith("openai/"):
            from lmql.runtime.openai_integration import openai_model

            # hard-code openai/ namespace to be openai-API-based
            adapter = openai_model(model_identifier[7:], endpoint=endpoint, **kwargs)
            return cls(original_name, adapter=adapter)
        else:
            from lmql.models.lmtp.lmtp_dcmodel import lmtp_model
            from lmql.models.lmtp.lmtp_dcinprocess import inprocess

            # special case for 'random' model (see random_model.py)
            if model_identifier == "random":
                kwargs["tokenizer"] = "gpt2" if "vocab" not in kwargs else kwargs["vocab"]
                kwargs["inprocess"] = True
                kwargs["async_transport"] = True

            # special case for 'llama.cpp'
            if model_identifier.startswith("llama.cpp:"):
                if "tokenizer" not in kwargs:
                    warnings.warn("By default LMQL uses the '{}' tokenizer for all llama.cpp models. To change this, set the 'tokenizer' argument of your lmql.model(...) object.".format("huggyllama/llama-7b", UserWarning))
                kwargs["tokenizer"] = kwargs.get("tokenizer", "huggyllama/llama-7b")

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
            
            return cls(original_name, adapter=Model())

"""
The default model for workloads or queries that do not specify 
a model explicitly.
"""
default_model = "openai/gpt-3.5-turbo-instruct"

def get_default_model() -> Union[str, LLM]:
    """
    Returns the default model instance to be used when no 'from' clause or @lmql.query(model=<model>) are specified.

    This applies globally in the current process.
    """
    global default_model
    return default_model

def set_default_model(model: Union[str, LLM]):
    """
    Sets the model instance to be used when no 'from' clause or @lmql.query(model=<model>) are specified.

    This applies globally in the current process.
    """
    global default_model
    default_model = model


"""
Lazily initialized query to generate text from an LLM using the .generate(...) 
and .generate_sync(...) methods.
"""
_generate_query = None
def get_generate_query():
    global _generate_query
    if _generate_query is None:
        @query
        async def generate_query(prompt, max_tokens=32):
            '''lmql
            "{prompt}[RESPONSE]" where len(TOKENS(RESPONSE)) < max_tokens
            return context.prompt
            '''
        _generate_query = generate_query
    return _generate_query

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