from typing import Tuple
from lmql.models.lmtp.backends.lmtp_model import LMTPModel, LMTPModelResult, TokenStreamer
import random

import numpy as np
import lmql.utils.nputil as nputil

class UniformRandomSamplingLLM(LMTPModel):
    def __init__(self, seed=None, vocab=None, **kwargs):
        self.seed = seed
        self.kwargs = kwargs

        if vocab is not None:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(vocab)
            print("Random model using tokenizer", tokenizer)
            self._eos_token_id = tokenizer.eos_token_id
            self._vocab_size = tokenizer.vocab_size
        else:
            self._eos_token_id = 50256
            self._vocab_size = 50257

    @property
    def eos_token_id(self):
        return self._eos_token_id
    
    @property
    def vocab_size(self):
        return self._vocab_size

    # def score(self, input_ids: torch.LongTensor, attention_mask: torch.LongTensor, **model_kwargs) -> Tuple[torch.FloatTensor, torch.FloatTensor]:
    #     return super().score(input_ids, attention_mask, **model_kwargs)
    
    def generate(self, input_ids, attention_mask, 
                 temperature: float, max_new_tokens: int, 
                 bias_tensor, streamer: TokenStreamer) -> LMTPModelResult:
        if self.seed is not None:
            seed = input_ids.sum() + self.seed
            rng = np.random.RandomState(seed)
        else:
            rng = np.random.RandomState()
        
        scores = []
        
        if bias_tensor is not None:
            bias_tensor = self.make_bias_tensor(bias_tensor, self.vocab_size)

        for i in range(max_new_tokens):
            logits = np.zeros([len(input_ids), self.vocab_size])
            
            if bias_tensor is not None:
                logits += bias_tensor
            
            logits = logits - np.log(np.exp(logits).sum(axis=-1)).reshape(-1,1)
            probs = np.exp(logits)

            next_ids = np.array([rng.choice(logits.shape[-1], size=1, p=probs[i]) for i in range(len(probs))]).reshape(-1,1)

            for i,j in enumerate(next_ids):
                logits[i, j.item()] += 1e-2
            
            scores += [nputil.log_softmax(logits, axis=-1)]
            input_ids = np.concatenate([input_ids, next_ids], axis=-1)
            
            streamer(input_ids, scores)

        return LMTPModelResult(sequences=input_ids, scores=scores)
    
LMTPModel.registry["random"] = UniformRandomSamplingLLM