import numpy as np
import asyncio

from lmql.model.served_model import ServedPretrainedModel
import lmql.runtime.dclib as dc
from lmql.runtime.tokenizer import load_tokenizer


def transformers_model(endpoint, model_identifier):
    import torch

    class NumpyBridgedServedPretrainedModel(ServedPretrainedModel):
        def __init__(self, transformers_model: 'TransformersModel', *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.transformers_model = transformers_model
        
        async def tokenize(self, text):
            return await self.transformers_model.tokenize(text)

        async def detokenize(self, input_ids):
            return await self.transformers_model.detokenize(input_ids)

        def __getattribute__(self, __name: str):
            if __name == "__dict__":
                return super().__getattribute__(__name)
            value = super().__getattribute__(__name)
            
            if callable(value):
                def bridge_tensor(v):
                    if type(v) is np.ndarray:
                        return torch.from_numpy(v)
                    if type(v) is list:
                        return [bridge_tensor(a) for a in v]
                    return v
                def proxy(*args, **kwargs):
                    args = [bridge_tensor(a) for a in args]
                    kwargs = {k: bridge_tensor(v) for k, v in kwargs.items()}
                    return value(*args, **kwargs)
                return proxy
            
            return value

    class TransformersModel:
        def __init__(self):
            self.model_identifier = model_identifier
            local = self.model_identifier.startswith("local:")
            if local:
                self.model_identifier = self.model_identifier.split(":")[1]
            self.served_model = NumpyBridgedServedPretrainedModel(self, endpoint, self.model_identifier, use_tq=False, local=local)

            self.tokenizer = load_tokenizer(self.model_identifier)

        def get_tokenizer(self):
            return self.tokenizer

        def sync_tokenize(self, text):
            return self.get_tokenizer()(text)["input_ids"]

        async def tokenize(self, text):
            async def task(text):
                input_ids = self.get_tokenizer()(text)["input_ids"]
                # strip off bos if present, LMQL handles this internally
                if len(input_ids) > 0 and input_ids[0] == self.tokenizer.bos_token_id:
                    input_ids = input_ids[1:]
                return [i for i in input_ids if i is not None]
            t = asyncio.create_task(task(text))
            return (await t)
        
        async def detokenize(self, input_ids):
            async def task(input_ids):
                input_ids = [i for i in input_ids if i is not None]
                return self.get_tokenizer().decode(input_ids)
            t = asyncio.create_task(task(input_ids))
            return (await t)

        def get_dclib_model(self):
            dc.set_dclib_tokenizer(self.get_tokenizer())
            return dc.DcModel(self.served_model, self.tokenizer)
    
    return TransformersModel