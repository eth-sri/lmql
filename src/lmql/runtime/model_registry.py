from lmql.models.model import LMQLModelDescriptor, inprocess, LMQLModel
import os
import warnings

"""
Model name aliases to enable more convenient access to 
popular models.
"""
model_name_aliases = {
    "chatgpt": "openai/gpt-3.5-turbo",
    "gpt-4": "openai/gpt-4",
}
class LMQLModelRegistry: 
    """
    Central registry of models and backends that can be used in LMQL.

    Use get() to resolve a LMQLModelDescriptor to a usable LMQLModel.
    """
    backend_configuration = None

    @staticmethod
    def get(model, **kwargs):
        if model == "<dynamic>":
            model = LMQLModelRegistry.default_model

        if model in model_name_aliases:
            model = model_name_aliases[model]

        if type(model) is LMQLModelDescriptor:
            if model.model is not None:
                return model.model
            else:
                kwargs = {**model.kwargs, **kwargs}
                model = model.model_identifier

        return resolve(model, **kwargs)

def resolve(model_name, endpoint=None, **kwargs) -> LMQLModel:
    """
    Automatically registers a model backend implementation for the provided
    model name, deriving the implementation from the model name.
    """
    if model_name.startswith("openai/"):
        from lmql.runtime.openai_integration import openai_model

        # hard-code openai/ namespace to be openai-API-based
        return openai_model(model_name[7:], endpoint=endpoint, **kwargs)
    else:
        from lmql.models.lmtp.lmtp_dcmodel import lmtp_model

        # special case for 'random' model (see random_model.py)
        if model_name == "random":
            kwargs["tokenizer"] = "gpt2" if "vocab" not in kwargs else kwargs["vocab"]
            kwargs["inprocess"] = True
            kwargs["async_transport"] = True

        # special case for 'llama.cpp'
        if model_name.startswith("llama.cpp:"):
            if "tokenizer" not in kwargs:
                warnings.warn("By default LMQL uses the '{}' tokenizer for all llama.cpp models. To change this, set the 'tokenizer' argument of your lmql.model(...) object.".format("huggyllama/llama-7b", UserWarning))
            kwargs["tokenizer"] = kwargs.get("tokenizer", "huggyllama/llama-7b")

        # determine endpoint URL
        if endpoint is None:
            endpoint = "localhost:8080"

        # determine model name and if we run in-process
        if model_name.startswith("local:"):
            model_name = model_name[6:]
            kwargs["inprocess"] = True

        if kwargs.get("inprocess", False):
            Model = inprocess(model_name, use_existing_configuration=True, **kwargs).model
        else:
            Model = lmtp_model(model_name, endpoint=endpoint, **kwargs)
        
        return Model

LMQLModelRegistry.autoconnect = None

# instance of model clients in this process
LMQLModelRegistry.default_model = "openai/text-davinci-003"