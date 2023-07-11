from typing import Tuple

import numpy as np
from llama_cpp import Llama, LlamaTokenizer

import lmql.utils.nputil as nputil
from lmql.models.lmtp.backends.lmtp_model import (LMTPModel, LMTPModelResult,
                                                  TokenStreamer)

class LlamaCppModel(LMTPModel):
    def __init__(self, model_identifier, **kwargs):
        self.model_identifier = model_identifier
        self.kwargs = kwargs

        print("[Loading llama.cpp model from", self.model_identifier, "]", flush=True)
        self.llm = Llama(model_path=model_identifier.strip("llama.cpp:"), **kwargs)

    def eos_token_id(self):
        return 2

    # def score(self, input_ids: torch.LongTensor, attention_mask: torch.LongTensor, **model_kwargs) -> Tuple[torch.FloatTensor, torch.FloatTensor]:
    #     return super().score(input_ids, attention_mask, **model_kwargs)
    
    def generate(self, input_ids, attention_mask, 
                 temperature: float, max_new_tokens: int, 
                 bias_tensor, streamer: TokenStreamer) -> LMTPModelResult:
        token_scores = []
        sequence = []

        input_ids = input_ids.reshape(-1).tolist()

        def llama_streamer(tokens, scores):
            nonlocal token_scores, sequence
            scores = np.array(scores)
            scores = nputil.log_softmax(scores, axis=-1)
            token_scores.append(scores)
            return False

        logits_processor = self.logits_processors(bias_tensor) if bias_tensor is not None else None

        print(input_ids, flush=True)

        for i, token in zip(range(max_new_tokens), self.llm.generate(input_ids, max_new_tokens, 
                                                            temp=temperature,
                                                            stopping_criteria=llama_streamer, 
                                                            logits_processor=logits_processor)):
            sequence += [token]
            sq_ar = np.array(sequence)
            ts_ar = np.stack(token_scores, axis=0)
            streamer(sq_ar.reshape(1, *sq_ar.shape), ts_ar.reshape(-1, 1, *ts_ar.shape[1:]))
        
        ts_ar = np.stack(token_scores, axis=0)
        sq_ar = np.array(sequence)

        return LMTPModelResult(
            sequences=sq_ar.reshape(1, *sq_ar.shape),
            scores=ts_ar.reshape(-1, 1, *ts_ar.shape[1:])
        )

    def logits_processors(self, logit_biases):
        bias_tensors = None
        make_bias_tensor = self.make_bias_tensor
        
        if len(logit_biases) == 0:
            return []

        class BatchLogitsProcessor:
            def __call__(self, input_ids, scores):
                nonlocal bias_tensors

                scores = np.array(scores)

                if bias_tensors is None:
                    bias_tensors = np.array(make_bias_tensor(logit_biases, scores.shape[-1]))

                return (scores + bias_tensors).reshape(-1)
        
        return BatchLogitsProcessor()

LMTPModel.registry["llama.cpp"] = LlamaCppModel

if __name__ == "__main__":
    from transformers import AutoTokenizer
   
    llm = Llama("/Users/luca/Developer/llama.cpp/models/7B/ggml-model-q4_0.bin")
    s = "Say this is a test:"
    tokenizer = AutoTokenizer.from_pretrained("huggyllama/llama-7b")
    ids = tokenizer(s)["input_ids"]
    print(ids)

    for token in llm.generate(ids, 120, temp=0.0):
        ids += [token]
        print(tokenizer.decode(ids))