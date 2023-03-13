class LMQLModelRegistry: pass

model_name_aliases = {
    "chatgpt": "openai/gpt-3.5-turbo"
}

LMQLModelRegistry.registry = {}
# instance of model clients in this process
LMQLModelRegistry.clients = {}

def get_model(model):
    client = LMQLModelRegistry.clients.get(model, None)

    if client is None:
        # use auto connector to obtain model connection
        if LMQLModelRegistry.autoconnect is not None and model not in LMQLModelRegistry.registry:
            LMQLModelRegistry.autoconnect(model)

        client = LMQLModelRegistry.registry[model]()
        LMQLModelRegistry.clients[model] = client

    return client

LMQLModelRegistry.get = get_model
LMQLModelRegistry.autoconnect = None