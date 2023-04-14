"""
Implementation of on-the-fly input_id rewriting 
during decoding.
"""

from typing import Optional, Dict, Any, Union

from dataclasses import dataclass
from typing import List
import asyncio

import numpy as np
from lmql.utils import nputil

from lmql.runtime.decoder_head import DecoderHead


@dataclass
class ActivePromptTokens:
    next_tokens: np.ndarray # long
    is_actively_prompted: np.ndarray # bool

def dim(t):
    if type(t) is int:
        return 0
    elif type(t) is list:
        if len(t) == 0:
            return 2
        return 1 + dim(t[0])
    elif nputil.is_array(t):
        return t.ndim
    else:
        raise Exception("ndim not implemented for type: " + str(type(t)))

@dataclass
class RewrittenInputIds:
    appended_input_ids: List[np.ndarray]
    strip_eos: bool = True
    user_data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None
    value_offset: Optional[int] = None

    def strip_ids(self, input_ids, i):
        if self.strip_eos == True:
            return input_ids[i,:-1]
        elif type(self.strip_eos) is list:
            sequence_strip = self.strip_eos[i]
            if sequence_strip == True:
                return input_ids[i,:-1]
            elif type(sequence_strip) is int:
                return input_ids[i,:sequence_strip]
            else:
                return input_ids[i]
        else:
            return input_ids[i]

    def setting_user_data(self, key, value):
        if self.user_data is None:
            self.user_data = {}
        self.user_data[key] = value
        return self

    def append(self, input_ids: np.ndarray):
        to_append = self.appended_input_ids
        if to_append is None: to_append = [np.array([], dtype=np.int64, device=input_ids.device) for _ in range(len(input_ids))]

        # concat existing input_ids (minus eos if self.strip_eos) with appended input_ids (head_seqs)
        input_ids = [np.concatenate([self.strip_ids(input_ids, i), ids], axis=-1) for i, ids in enumerate(to_append)]

        return input_ids

    def append_and_left_pad(self, input_ids: np.ndarray):
        device =  input_ids.device
        input_ids = self.append(input_ids)
        max_length = max(len(seq) for seq in input_ids)
                
        # padding masks
        seqs_padding = [max_length - len(seq) for seq in input_ids]
        seqs_padding = np.stack([np.arange(max_length) < padding for padding in seqs_padding], axis=0)
        # pad actual input IDs
        input_ids = np.stack([left_pad(seq, max_length) for seq in input_ids], axis=0)
        
        assert input_ids.dtype == np.int64
        
        return input_ids, seqs_padding

    @staticmethod
    def with_user_data(rewritten_ids, key, value):
        if rewritten_ids is None: 
            rewritten_ids = RewrittenInputIds(appended_input_ids=None, strip_eos=False)
        return rewritten_ids.setting_user_data(key, value)

def left_pad(t, n, value = -1):
    if len(t) >= n: return t
    return np.concatenate([np.ones(n - len(t), dtype=np.int64) * value, t], axis=0)

class InputIdRewriter:
    def __init__(self, head_rewriter, tokenize, detokenize, eos_token_id, initial_prompt_offset):
        self.head_rewriter = head_rewriter
        
        self.tokenize = tokenize
        self.detokenize = detokenize

        self.eos_token_id = eos_token_id
        self.initial_prompt_offset = initial_prompt_offset

    async def rewrite_seq(self, i: int, head_input_ids, next_token_scores, next_token_logprob: Optional[np.ndarray], mask_seq_to_rewrite: Optional[np.ndarray] = None, user_data=None):
        # only rewrite masked sequences if a mask is provided
        if mask_seq_to_rewrite is not None:
            if not mask_seq_to_rewrite[i]:
                return None

        head = DecoderHead(i, 
            head_input_ids[:-1], head_input_ids[-1], next_token_scores[i],
            self.tokenize,
            self.detokenize,
            self.eos_token_id,
            self.initial_prompt_offset,
            next_token_logprob = next_token_logprob[i] if next_token_logprob is not None else None,
            user_data = user_data
        )
        return await self.head_rewriter(head)

    async def input_ids_rewriter_fn(self, input_ids, next_token_scores, seq_idx = None, next_token_logprob = None, mask_seq_to_rewrite = None, user_data=None):
        assert dim(input_ids) == 2, "input_ids must be a 2D tensor"

        def get_user_data(i):
            if user_data is None: 
                return None
            return user_data[i]
        
        head_results: List[RewrittenInputIds] = await asyncio.gather(*(self.rewrite_seq(i, head_input_ids, next_token_scores, next_token_logprob, mask_seq_to_rewrite, user_data=get_user_data(i)) for i, head_input_ids in enumerate(input_ids)))

        if all(r is None for r in head_results):
            # note: user data will be lost here
            return RewrittenInputIds(appended_input_ids=None, strip_eos=False, user_data=[None for _ in range(len(input_ids))], value_offset=[None for _ in range(len(input_ids))])
        else:
            strip_eos = [r.strip_eos if r is not None else False for r in head_results]
            if all([s == True for s in strip_eos]): strip_eos = True

            # collect appended input ids
            appended_seqs = [rewrite.appended_input_ids if rewrite is not None else [] for rewrite in head_results]
            appended_seqs = [nputil.ensure_array(seq) for seq in appended_seqs]

            # collect user data
            user_data = [rewrite.user_data if rewrite is not None else None for rewrite in head_results]
            
            # handle case where nothing needs to be appended but we still need to strip eos
            if all(seq is None for seq in appended_seqs):
                appended_seqs = None

            # value offsets
            value_offset = [rewrite.value_offset if rewrite is not None else None for rewrite in head_results]

            return RewrittenInputIds(appended_input_ids=appended_seqs, strip_eos=strip_eos, user_data=user_data, value_offset=value_offset)

class ActivePromptingRewriter:
    def __init__(self, head_rewriter, tokenize, detokenize, eos_token_id, initial_prompt_offset):
        self.head_rewriter = head_rewriter
        
        self.tokenize = tokenize
        self.detokenize = detokenize

        self.eos_token_id = eos_token_id
        self.initial_prompt_offset = initial_prompt_offset

    async def input_ids_rewriter_fn(self, input_ids, active: bool):
        assert active, "ActivePromptingRewriter should only be used when actively prompting (active=True)"
        # print("ActivePromptingRewriter: input_ids", len(input_ids))

        head_results: List[ActivePromptTokens] = [
            await self.head_rewriter(DecoderHead(i, 
                head_input_ids[:-1], head_input_ids[-1], None,
                self.tokenize,
                self.detokenize,
                self.eos_token_id,
                self.initial_prompt_offset))
        for i, head_input_ids in enumerate(input_ids)]

        if all(r is None for r in head_results):
            all_zeros = np.zeros(input_ids.shape[0], device=input_ids.device, dtype=np.int64)
            return ActivePromptTokens(next_tokens=all_zeros, is_actively_prompted=all_zeros.clone())
        else:
            next_tokens = np.array([next_token if next_token is not None else -1 for next_token in head_results], device=input_ids.device, dtype=np.int64)
            is_actively_prompted = np.array([1 if r is not None else 0 for r in head_results], device=input_ids.device, dtype=np.int64)
            return ActivePromptTokens(next_tokens=next_tokens, is_actively_prompted=is_actively_prompted)