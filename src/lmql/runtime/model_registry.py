from lmql.models.model import LMQLModel, inprocess
import os

model_name_aliases = {
    "chatgpt": "openai/gpt-3.5-turbo",
    "gpt-4": "openai/gpt-4",
}
class LMQLModelRegistry: 
    """
    Central registry of models and backends that can be used in LMQL.
    """
    backend_configuration = None

    @staticmethod
    def get(model, **kwargs):
        if model == "<dynamic>":
            model = LMQLModelRegistry.default_model

        if model in model_name_aliases:
            model = model_name_aliases[model]

        if type(model) is LMQLModel:
            if model.model is not None:
                return model.model
            else:
                kwargs = {**model.kwargs, **kwargs}
                model = model.model_identifier

        client = LMQLModelRegistry.clients.get(model, None)

        if client is None:
            # use resolve to obtain model connection from model identifier
            if model not in LMQLModelRegistry.registry:
                resolve(model, **kwargs)

            # strip off local
            if model.startswith("local:"):
                model = model[6:]

            client = LMQLModelRegistry.registry[model]()
            LMQLModelRegistry.clients[model] = client

        return client

def resolve(model_name, endpoint=None, **kwargs):
    """
    Automatically registers a model backend implementation for the provided
    model name, deriving the implementation from the model name.
    """
    if model_name.startswith("openai/"):
        from lmql.runtime.openai_integration import openai_model

        # hard-code openai/ namespace to be openai-API-based
        Model = openai_model(model_name[7:], endpoint=endpoint, **kwargs)
        register_model(model_name, Model)
        register_model("*", Model)
    else:
        from lmql.models.lmtp.lmtp_dcmodel import lmtp_model

        # special case for 'random' model (see random_model.py)
        if model_name == "random":
            kwargs["tokenizer"] = "gpt2"
            kwargs["inprocess"] = True
            kwargs["async_transport"] = True

        # special case for 'llama.cpp'
        if model_name.startswith("llama.cpp:"):
            # kwargs["async_transport"] = True
            kwargs["tokenizer"] = "huggyllama/llama-7b"

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
        
        register_model(model_name, Model)
        return

def register_model(identifier, ModelClass):
    LMQLModelRegistry.registry[identifier] = ModelClass

LMQLModelRegistry.autoconnect = None

LMQLModelRegistry.registry = {}
# instance of model clients in this process
LMQLModelRegistry.clients = {}
LMQLModelRegistry.default_model = "openai/text-davinci-003"