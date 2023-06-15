from lmql.models.model import model, LMQLModel, inprocess
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
        if model in model_name_aliases:
            model = model_name_aliases[model]

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
        try:
            import transformers
        except:
            if "LMQL_BROWSER" in os.environ:
                assert False, "The browser distribution of LMQL does not support HuggingFace Transformers models.\
                    Please use openai/ models or install lmql with 'transformers' support (pip install lmql[hf])."
            else:
                assert False, "Your distribution of LMQL does not support HuggingFace Transformers models.\
                    Please use openai/ models or install lmql with 'transformers' support (pip install lmql[hf])."

        from lmql.models.lmtp.lmtp_dcmodel import lmtp_model

        # special case for 'random' model (see random_model.py)
        if model_name == "random":
            kwargs["tokenizer"] = "gpt2"
            kwargs["inprocess"] = True

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