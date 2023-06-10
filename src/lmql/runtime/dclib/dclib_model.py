import asyncio
from collections import namedtuple
from typing import List, Union

from .dclib_array import DataArray
from .dclib_rewrite import DcModelRewriteMixin
from .dclib_global import stats
from .dclib_seq import DecoderSequence, detseq, deepcopy, deepmerge, DecoderSequence, DeterministicDecoderSequence, Continuation
import numpy as np
from lmql.utils import nputil
import lmql.runtime.masks as masks
from dataclasses import dataclass
import sys

from lmql.runtime.stats import Stats

class CacheDelegate:
    def register_token_stream(self, fut: callable):
        """
        Registers an async iterator as an active token stream.

        A token stream is an async generator function of (s, token, score, edge_type) tuples, where 
        - 's' is a DecoderSequence,
        - 'token' is the token to be appended to 's',
        - 'score' is the logprob of 'token' given 's',
        - 'edge_type' is the type of edge that was used to expand 's' to 's + token'.
        """
        pass

class DcModel(DcModelRewriteMixin):
    def __init__(self, model, tokenizer, truncation_threshold=-3e38, init_workers=True, textmode=False, **kwargs):
        """
        An abstract interface of an LLM used in the decoder.

        For concrete implementations, see openai_integration.py and lmtp_dcmodel.py.
        
        model: The model to use for inference.
        bos_token_id: The token id to use for the beginning of a sequence.
        eos_token_id: The token id to use for the end of a sequence.
        truncation_threshold: The threshold to use for logit truncation (cf. DecoderSequence.truncation_threshold). Logits below this threshold are considered to be -inf and will never be considered as next token.
        """
        self.model = model
        self.tokenizer = tokenizer
        self.model_identifier = model.model_identifier
        self.model_args = kwargs

        self.bos_token_id = tokenizer.bos_token_id
        self.eos_token_id = tokenizer.eos_token_id
        self.eos = self.tokenizer.decode_bytes([self.eos_token_id])[0]
        
        self.truncation_threshold = truncation_threshold

        self.stats = Stats("dcmodel")

        # if set, the cache delegate can be called for speculative model scoring results 
        # (e.g. when sequences are scored in speculatively).
        self.cache_delegate: CacheDelegate = None

    def register_token_stream(self, task):
        if self.cache_delegate is not None:
            self.cache_delegate.register_token_stream(task)

    def log_billable_tokens(self, n: int):
        if hasattr(self.model, "billable_tokens"):
            self.model.billable_tokens += n
        
    def log_queries(self, n: int):
        if hasattr(self.model, "num_queries"):
            self.model.num_queries += n

    async def detokenize(self, *args, **kwargs):
        return await self.model.detokenize(*args, **kwargs)
    
    async def tokenize(self, *args, **kwargs):
        return await self.model.tokenize(*args, **kwargs)

    async def compute_logits_mask(self, input_ids, user_data, is_constrained, seqs, required=False, **kwargs):
        if "modern_logits_processor" in kwargs:
            processor = kwargs["modern_logits_processor"]
            mask = await processor(seqs, additional_logits_processor_mask=is_constrained, **kwargs)
            return mask

        assert not required, "compute_logits_mask() cannot produce a token mask, as the provided kwargs do not contain a logits processor. Please make sure to pass a logits processor to decoding function you are using."
        return namedtuple("LogitsMaskResult", ["logits_mask", "user_data"])([None], user_data)

    async def argmax(self, sequences, **kwargs):
        """
        Returns a pool with `n` sampled successor nodes per node in the pool.
        """
        raise NotImplementedError()

    async def score(self, sqs: List[DecoderSequence], tokens: List[List[int]], max_batch_size=None, deterministic: Union[bool, List[bool]]=False, stop_phrase=False, needs_rewrite=True, user_data=None, noscore=False, internal=False):
        raise NotImplementedError()
        
    async def score_tokens(self, sqs: List[DecoderSequence], tokens: List[List[int]], max_batch_size=None, noscore=False):
        """
        Iterates the scores for 'tokens' when appended to the sequences in 'sqs', element-wise.

        Returns:
            List of tuples (sqs[i], tokens[i], scores(token[i]))
        """
        raise NotImplementedError()

    async def topk_continuations(self, sequences, k, **kwargs):
        raise NotImplementedError()
    
    def report_stats(self, printer, decoder_step=None):
        self.model.report_stats(printer, decoder_step)

def model(model=None, **kwargs) -> DcModel:
    if "dcmodel" in kwargs:
        return kwargs["dcmodel"]
    if issubclass(type(model), DcModel):
        model.model_args = {**model.model_args, **kwargs}
        return model
    return DcModel(model, **kwargs)