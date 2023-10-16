from typing import Tuple
from lmql.models.lmtp.backends.lmtp_model import LMTPModel, LMTPModelResult, TokenStreamer
import lmql
import random
import asyncio
import os
import openai

import numpy as np
import lmql.utils.nputil as nputil

class TextModel(LMTPModel):
    def __init__(self, seed=None, output=None, **kwargs):
        self.seed = seed or 0
        self.kwargs = kwargs

        if kwargs.get("verbose", False):
            print("['text' model using seed {}]".format(seed))

        os.environ["TOKENIZERS_PARALLELISM"] = "true"

        from transformers import AutoTokenizer
        tokenizer = lmql.tokenizer("tokenizer:gpt-3.5-turbo")
        if kwargs.get("verbose", False):
            print("['text' model using tokenizer {}]".format(tokenizer))
        self.tokenizer = tokenizer
        self._eos_token_id = tokenizer.eos_token_id
        self._vocab_size = tokenizer.vocab_size

        self.output = ([self._eos_token_id] + tokenizer(output)["input_ids"]) if output else None

    def model_info(self):
        return "TextModel(seed={})".format(self.seed)

    @property
    def eos_token_id(self):
        return self._eos_token_id
    
    @property
    def vocab_size(self):
        return self._vocab_size

    async def generate(self, input_ids, attention_mask, 
                 temperature: float, max_new_tokens: int, 
                 bias_tensor, streamer: TokenStreamer, **kwargs) -> LMTPModelResult:
        scores = []
        
        if bias_tensor is not None:
            bias_tensor = self.make_bias_tensor(bias_tensor, self.vocab_size)

        prompt = self.tokenizer.decode(input_ids[0])
        ids = self.output or input_ids
        i = 0
        print("max_new_tokens", max_new_tokens, flush=True)

        async for chunk in await openai.ChatCompletion.acreate(
            stream=True,
            model="gpt-3.5-turbo",
            temperature=temperature,
            **kwargs,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_new_tokens if max_new_tokens < 40_000 else None
        ):
            if "content" not in chunk.choices[0].delta.keys():
                # this indicates stopping
                text = "<|endoftext|>"
            else:
                text = chunk.choices[0].delta.content

            if len(text) == 0:
                continue

            ids = self.tokenizer(text)["input_ids"]

            for id in ids:
                logits = np.zeros([len(input_ids), self.vocab_size])
                
                if bias_tensor is not None:
                    logits += bias_tensor
                
                logits = logits - np.log(np.exp(logits).sum(axis=-1)).reshape(-1,1)
                next_ids = np.array([id]).reshape(-1,1)

                for k,j in enumerate(next_ids):
                    logits[k, j.item()] += 1e-2
                
                scores += [nputil.log_softmax(logits, axis=-1)]
                input_ids = np.concatenate([input_ids, next_ids], axis=-1)
                
                if i+1 >= max_new_tokens:
                    break

                streamer(input_ids, scores)

                await asyncio.sleep(0)

        return LMTPModelResult(sequences=input_ids, scores=scores)
    
LMTPModel.registry["text"] = TextModel