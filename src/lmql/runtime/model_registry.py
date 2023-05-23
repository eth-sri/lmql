import os

model_name_aliases = {
    "chatgpt": "openai/gpt-3.5-turbo",
    "gpt-4": "openai/gpt-4",
}
class LMQLModelRegistry: 
    autoconnect = False
    backend_configuration = None

    @staticmethod
    def get(model):
        client = LMQLModelRegistry.clients.get(model, None)

        if client is None:
            # use auto connector to obtain model connection
            if LMQLModelRegistry.autoconnect and model not in LMQLModelRegistry.registry:
                autoregister(model)

            # strip off local
            if model.startswith("local:"):
                model = model[6:]

            client = LMQLModelRegistry.registry[model]()
            LMQLModelRegistry.clients[model] = client

        return client

def autoregister(model_name):
    """
    Automatically registers a model backend implementation for the provided
    model name, deriving the implementation from the model name.
    """
    if model_name.startswith("openai/"):
        from lmql.runtime.openai_integration import openai_model

        # hard-code openai/ namespace to be openai-API-based
        Model = openai_model(model_name[7:])
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

        if LMQLModelRegistry is not None:
            backend: str = LMQLModelRegistry.backend_configuration
            if backend == "legacy":
                from lmql.runtime.hf_integration import transformers_model

                default_server = "http://localhost:8080"
                Model = transformers_model(default_server, model_name)
                
                if model_name.startswith("local:"):
                    model_name = model_name[6:]
                
                register_model(model_name, Model)
            else:
                from lmql.runtime.openai_integration import openai_model

                # determine endpoint URL
                if backend is None:
                    backend = "localhost:8080"

                # determine model name and if we run in-process
                if model_name.startswith("local:"):
                    from lmql.model.serve_oai import inprocess
                    
                    model_name = model_name[6:]
                    inprocess(model_name, use_existing_configuration=True)

                # use provided inference server as mocked OpenAI API
                endpoint = backend
                Model = openai_model(model_name, endpoint=endpoint, mock=True)
                register_model(model_name, Model)
                return

def register_model(identifier, ModelClass):
    LMQLModelRegistry.registry[identifier] = ModelClass

LMQLModelRegistry.autoconnect = None

LMQLModelRegistry.registry = {}
# instance of model clients in this process
LMQLModelRegistry.clients = {}