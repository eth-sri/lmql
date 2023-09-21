from lmql.runtime.tokenizer import LMQLTokenizer
from lmql.runtime.dclib.dclib_model import DcModel
from typing import Any
from abc import ABC, abstractmethod
from lmql.models.lmtp.utils import rename_model_args

import warnings

class LMQLModelDescriptor:
    """
    Descriptor base class for results of lmql.model(...) calls.

    The actual model runs either remotely (lmql serve-model), in-process via self.model or
    is accessed via API (e.g. OpenAI).

    Use LMQLModelRegistry.get to resolve a descriptor into a usable LMQLModel.
    """

    def __init__(self, model_identifier, model=None, **kwargs):
        self.model_identifier = model_identifier
        self.kwargs = kwargs

        # if this is a fixed reference to an existing model
        self.model = model

    def __repr__(self) -> str:
        return str(self)
    
    def __str__(self):
        return "<LMQLModelDescriptor: {}>".format(self.model_identifier)

LMQLModelDescriptor.inprocess_instances = {}

class LMQLModel(ABC):
    """
    Abstract base class for models (interface to integrate LMTP or OpenAI API)
    """
    
    @abstractmethod
    def get_tokenizer(self) -> LMQLTokenizer:
        """
        Returns the tokenizer used by this model.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_dclib_model(self) -> DcModel:
        """
        Returns the dclib DcModel handle to use this model.

        This handle is used for token generation and decoding via
        its methods like `argmax`, `sample` and `score`.
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

    @abstractmethod
    def sync_tokenize(self, text):
        """
        Synchroneous version of `tokenize`.
        """
        raise NotImplementedError()

def inprocess(model_name, use_existing_configuration=False, **kwargs):
    """
    Loads a 'transformers' model in-process and returns an LMQLModelDescriptor object
    to use this in-process model in LMQL.

    This is useful when you don't want to spawn a separate 'lmql serve-model' process.

    The returned in-process models are cached so that subsequent calls with the same arguments will return the same object.

    Args:
        model_name (str): Name of the model to load, as it occurs in the HuggingFace Transformers registry. (e.g. gpt2)
        
        use_existing_configuration (bool): If True, will return an existing in-process model with the same model name, but possibly different arguments.
        
        kwargs: Additional arguments to pass to the serve-model command line. (see lmql serve-model --help)
                For this, use keys as they occur in the command line, e.g. 'port' for '--port' and for
                boolean flags, use True/False as values, e.g. 'cuda=True' for '--cuda'.
    Return:
        InProcessServer: An object representing the loaded model, can be passed in the 'from' clause of a query.
    """
    from .lmtp.lmtp_dcmodel import lmtp_model
    assert not model_name.startswith("openai/"), "openai/ models cannot be loaded with inprocess=True, they always use the remote API."

    # extract/reassign renamed like 'cuda'
    kwargs = rename_model_args(kwargs)

    # special case for 'llama.cpp'
    if model_name.startswith("llama.cpp:"):
        # kwargs["async_transport"] = True
        if "tokenizer" not in kwargs:
            warnings.warn("By default LMQL uses the '{}' tokenizer for all llama.cpp models. To change this, set the 'tokenizer' argument of your lmql.model(...) object.".format("huggyllama/llama-7b", UserWarning))
        kwargs["tokenizer"] = kwargs.get("tokenizer", "huggyllama/llama-7b")

    if "endpoint" in kwargs:
        warnings.warn("info: 'endpoint' argument is ignored for inprocess=True/local: models.")

    cmdline_args = f"{model_name} "
    for k,v in kwargs.items():
        if type(v) is bool:
            cmdline_args += f"--{k} "
        else:
            cmdline_args += f"--{k} {v} "

    if cmdline_args in LMQLModelDescriptor.inprocess_instances.keys():
        model = LMQLModelDescriptor.inprocess_instances[cmdline_args]
        return LMQLModelDescriptor(model_name, model=model)

    kwargs["inprocess"] = True
    model = lmtp_model(model_name, **kwargs)
    LMQLModelDescriptor.inprocess_instances[cmdline_args] = model
    return LMQLModelDescriptor(model_name, model=model)

def model(model_identifier, **kwargs):
    """
    Constructs an LMQL model descriptor object to be used in 
    a `from` clause or as `model=<MODEL>` argument to @lmql.query(...).

    Examples:

    lmql.model("openai/gpt-3.5-turbo-instruct") # OpenAI API model
    lmql.model("random", seed=123) # randomly sampling model
    lmql.model("llama.cpp:<YOUR_WEIGHTS>.bin") # llama.cpp model
    
    lmql.model("local:gpt2") # load a `transformers` model in process
    lmql.model("local:gpt2", cuda=True, load_in_4bit=True) # load a `transformers` model in process with additional arguments
    """
    # handle inprocess models
    is_inprocess = kwargs.pop("inprocess", False) or model_identifier.startswith("local:")
    if is_inprocess and model_identifier.startswith("local:"):
        model_identifier = model_identifier[6:]

    if is_inprocess:
        return inprocess(model_identifier, **kwargs)
    else:
        return LMQLModelDescriptor(model_identifier, **kwargs)