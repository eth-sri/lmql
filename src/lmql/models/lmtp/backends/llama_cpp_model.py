from typing import Tuple
import sys

import numpy as np
from llama_cpp import Llama, LlamaTokenizer

import lmql.utils.nputil as nputil
from lmql.models.lmtp.backends.lmtp_model import (LMTPModel, LMTPModelResult,
                                                  TokenStreamer)

class LlamaCppModel(LMTPModel):
    def __init__(self, model_identifier, **kwargs):
        self.model_identifier = model_identifier
        self.kwargs = kwargs

        self.max_batch_size = 1

        print("[Loading llama.cpp model from", self.model_identifier, " with ", kwargs, "]", flush=True)
        if not "verbose" in kwargs.keys():
            kwargs["verbose"] = False
        self.llm = Llama(model_path=model_identifier[len("llama.cpp:"):], **kwargs)

    def eos_token_id(self):
        return 2

    def score(self, input_ids, attention_mask, **model_kwargs):
        import time
        # s = time.time()
        tokens = input_ids[0]

        if len(self.llm._input_ids) > 0:
            longest_prefix = 0
            for a, b in zip(self.llm._input_ids, tokens[:-1]):
                if a == b:
                    longest_prefix += 1
                else:
                    break
            if longest_prefix > 0:
                tokens = tokens[longest_prefix:]
                self.llm.n_tokens = longest_prefix

        self.llm.eval(tokens)
        logits = np.array(self.llm.scores)
        logits = nputil.log_softmax(logits, axis=-1)
        scores = np.array([logits[j][i] for j,i in enumerate(input_ids[0])])

        return scores.reshape(1, -1)
    
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

        for i, token in zip(range(max_new_tokens), self.llm.generate(input_ids, max_new_tokens, 
                                                            temp=temperature,
                                                            stopping_criteria=llama_streamer, 
                                                            logits_processor=logits_processor)):
            assert i + len(input_ids) < self.llm.n_ctx(), "The requested number of tokens exceeds the llama.cpp model's context size. Please specify a higher n_ctx value."
            
            if i > 0:
                streamer(sq_ar.reshape(1, *sq_ar.shape), ts_ar.reshape(-1, 1, *ts_ar.shape[1:]))
            sequence += [token]
            sq_ar = np.array(sequence)
            ts_ar = np.stack(token_scores, axis=0)

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