from typing import Tuple
import sys

import numpy as np

import lmql.utils.nputil as nputil
from lmql.models.lmtp.backends.lmtp_model import (LMTPModel, LMTPModelResult,
                                                  TokenStreamer)

class LlamaCppModel(LMTPModel):
    def __init__(self, model_identifier, **kwargs):
        from llama_cpp import Llama
        
        self.model_identifier = model_identifier
        self.kwargs = kwargs

        self.max_batch_size = 1

        print("[Loading llama.cpp model from", self.model_identifier, " with ", kwargs, "]", flush=True)
        if not "verbose" in kwargs.keys():
            kwargs["verbose"] = False
        self.llm = Llama(model_path=model_identifier[len("llama.cpp:"):], logits_all=True, **kwargs)

    def model_info(self):
        import llama_cpp
        return {
            "model_identifier": self.model_identifier[len("llama.cpp:"):],
            "model_type": "llama.cpp",
            "constructor": "Llama(model_path='{}'{})".format(self.model_identifier[len("llama.cpp:"):], ", " + ", ".join(["{}={}".format(k, v) for k,v in self.kwargs.items()]) if len(self.kwargs) > 0 else ""),
            "llama-cpp-python": llama_cpp.__version__,
        }

    def eos_token_id(self):
        return 2

    def score(self, input_ids, attention_mask, **model_kwargs):
        tokens = input_ids[0]

        # single forward pass (use generate() in favor of eval() to handle kv cache automatically)
        for _ in self.llm.generate(tokens, temp=0.0): break

        logits = np.array(self.llm.scores[:self.llm.n_tokens])
        logits = nputil.log_softmax(logits, axis=-1)
        scores = np.array([0.0] + [logits[j][i] for j,i in enumerate(input_ids[0][1:])])

        return scores.reshape(1, -1)
    
    def generate(self, input_ids, attention_mask, 
                 temperature: float, max_new_tokens: int, 
                 bias_tensor, streamer: TokenStreamer, **kwargs) -> LMTPModelResult:
        token_scores = []
        sequence = []

        input_ids = input_ids.reshape(-1).tolist()

        def llama_streamer(tokens, scores):
            nonlocal token_scores
            scores = np.array(scores)
            token_scores += [scores]
            return False

        logits_processor = self.logits_processors(bias_tensor) if bias_tensor is not None else None

        for i, token in zip(range(max_new_tokens), self.llm.generate(input_ids,
                                                            temp=temperature,
                                                            stopping_criteria=llama_streamer, 
                                                            logits_processor=logits_processor,
                                                            **kwargs)):
            assert i + len(input_ids) < self.llm.n_ctx(), "The requested number of tokens exceeds the llama.cpp model's context size. Please specify a higher n_ctx value."
            sequence += [token]
            sq_ar = np.array(sequence)
            ts_ar = np.stack(token_scores, axis=0)

            if i+1 >= max_new_tokens:
                break
            else:
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
                
                return nputil.log_softmax(scores + bias_tensors, axis=-1).reshape(-1)
        
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