import sys
from lmql.ops.token_set import TokenSetSymbolic, TokenSetConcrete

import numpy as np
from lmql.utils import nputil

class DecoderHead:
    def __init__(self, head: int, input_ids, next_token_id, next_token_logits: np.ndarray, tokenizer_fn, detokenizer_fn, eos_token_id, initial_prompt_offset, next_token_logprob=None, user_data=None):
        self.seq_idx: int = head
        
        self.input_ids = input_ids
        
        self.next_token_id = next_token_id
        if nputil.is_array(self.next_token_id): 
            self.next_token_id = nputil.item(self.next_token_id)
        self.next_token_logits = next_token_logits
        
        self.tokenizer_fn = tokenizer_fn
        self.detokenizer_fn = detokenizer_fn

        self.eos_token_id = eos_token_id
        self.initial_prompt_offset = initial_prompt_offset

        self.next_token_logprob = next_token_logprob
        
        self.user_data = user_data

    def is_at_eos(self):
        return self.next_token_id == self.eos_token_id

    @property
    def input_ids_without_padding(self):
        t = self.input_ids
        while len(t) > 0 and t[0] == self.eos_token_id:
            t = t[1:]
        return t

    async def text(self, offset=None, strip_padding=False, upper_bound=None, strip_eos=False, return_ids=False):
        if offset is None:
            offset = 0
        if upper_bound is None:
            upper_bound = len(self.input_ids)
        
        if offset == 0:
            while self.input_ids[offset] == self.eos_token_id:
                offset += 1
        else:
            for i in range(len(self.input_ids)):
                if self.input_ids[i] != self.eos_token_id: break
                else: offset += 1
        ids = self.input_ids[offset:upper_bound]
        while strip_eos and ids[-1] == self.eos_token_id:
            ids = ids[:-1]
        
        if return_ids:
            return await self.detokenizer_fn(ids), ids
        else:
            return await self.detokenizer_fn(ids)

    async def tokenize(self, t):
        return await self.tokenizer_fn(t)

    async def detokenize(self, input_ids):
        return await self.detokenizer_fn(input_ids)

    async def translate_mask(self, mask, vocab_size):
        m = np.ones([vocab_size], dtype=np.int32)

        if mask == "*":
            return None
        elif type(mask) is TokenSetSymbolic:
            # start with full mask for minussets (e.g. * \ {a,b,c})
            if not mask.minusset: 
                m[:] = 0
            
            for t in mask.tokens:
                # switch to something more unique
                if t == "eos": t = "<EOS>"
                
                token_id = (await self.tokenize(t))[0]
                m[token_id] = 0 if mask.minusset else 1

            return m
        else:
            assert type(mask) is TokenSetConcrete
            return mask.mask
    
    async def make_mask(self, *token_ids, vocab_size):
        m = np.zeros([vocab_size])
        for t in token_ids: m[t] = 1
        return m