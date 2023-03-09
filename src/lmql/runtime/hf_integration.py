from transformers import AutoTokenizer

from lmql.model.client import ServedPretrainedModel
from lmql.runtime.decoder_head import DecoderHead
from lmql.runtime.rewriter import InputIdRewriter, ActivePromptingRewriter
from lmql.runtime.tokenizer import load_tokenizer
from lmql.runtime.dclib.lmql_adapter import QueryDcLibAdapter
from lmql.runtime.dclib.dclib_model import DcModel
import numpy as np

# class EventualLocalTokenizer:
#     def __init__(self, model_identifier):
#         import threading

#         self.model_identifier = model_identifier
#         # use semaphor to access self._tokenizer
#         self._semaphore = threading.Semaphore()
#         self._tokenizer = None

#         # start separate thread to load tokenizer
#         self._thread = threading.Thread(target=self._load_tokenizer)
#         self._thread.start()
    
#     def _load_tokenizer(self):
#         t = AutoTokenizer.from_pretrained(self.model_identifier)
#         with self._semaphore: self._tokenizer = t

def transformers_model(endpoint, model_identifier):
    import torch

    class NumpyBridgedServedPretrainedModel(ServedPretrainedModel):
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

    class ServedModelInterfaceCls:
        def __init__(self):
            self.model_identifier = model_identifier
            local = self.model_identifier.startswith("local:")
            if local:
                self.model_identifier = self.model_identifier.split(":")[1]
            self.served_model = NumpyBridgedServedPretrainedModel(endpoint, self.model_identifier, use_tq=False, local=local)
            self.decoder_args = None

            self.active_prompting = False

            self._tokenizer = None

            self.bos_token_id = self.get_tokenizer().bos_token_id
            self.eos_token_id = self.get_tokenizer().eos_token_id

            self.adapter = QueryDcLibAdapter(self.get_tokenizer().vocab_size, self.tokenize, self.detokenize, self.bos_token_id, self.eos_token_id)
            self._dcmodel = None

        def get_tokenizer(self):
            if self._tokenizer is None:
                self._tokenizer = load_tokenizer(self.model_identifier) # AutoTokenizer.from_pretrained(self.model_identifier)
            return self._tokenizer

        def set_decoder(self, method, **kwargs):
            # defaults
            DEFAULTS = {
                "max_len": 512,
                "decoder": method
            }
            self.decoder_args = DEFAULTS.copy()

            # custom user arguments
            protected_args = set(["input_ids", "additional_logits_processors", "bos_token_id", "eos_token_id"])
            for key, value in kwargs.items():
                if key in protected_args:
                    print("warning: cannot override runtime determined decoder argument {}.".format(key))
                    continue
                self.decoder_args[key] = value

        async def score_distribution_values(self, prompt, values):
            self.served_model.num_generate_calls += len(values)
            return await self.adapter.score_distribution_values(prompt, values, self.get_dclib_model())

        def get_dclib_model(self):
            return DcModel(self.served_model, self.bos_token_id, self.eos_token_id, **self.decoder_args)

        async def query(self, prompt, mask_logits_processor, head_input_id_rewriter, active_prompt_rewriter):
            assert self.decoder_args is not None, "Cannot query() a model without calling set_decoder first."
            
            self.served_model.num_generate_calls += 1
            return await self.adapter.query(prompt, mask_logits_processor, head_input_id_rewriter, active_prompt_rewriter, self.get_dclib_model(), self.decoder_args)

        async def tokenize(self, text):
            input_ids = self.get_tokenizer()(text)["input_ids"]
            # strip off bos if present, LMQL handles this internally
            if len(input_ids) > 0 and input_ids[0] == self.bos_token_id:
                input_ids = input_ids[1:]
            return [i for i in input_ids if i is not None]
        
        async def detokenize(self, input_ids):
            input_ids = [i for i in input_ids if i is not None]
            return self.get_tokenizer().decode(input_ids)
    
    return ServedModelInterfaceCls