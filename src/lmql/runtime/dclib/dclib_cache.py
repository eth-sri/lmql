import asyncio
import numpy as np
import pickle
import os
from typing import List, Union

from .dclib_array import DataArray
from .dclib_seq import DecoderSequence, Continuation, DeterministicDecoderSequence, deepcopy, deepmerge
from .dclib_model import DcModel
import lmql.runtime.masks as masks
from lmql.utils.nputil import ensure_iterable

class CachedDcModel:
    def __new__(cls, delegate, initial_prompt_ids=None, cache_file=None):
        mc = super().__new__(cls)
        
        mc.delegate: DcModel = delegate
        
        mc.cache = {}
        mc.mask_cache = {}
        
        mc.input_id_key_offset = len(initial_prompt_ids) if initial_prompt_ids else 0
        mc.cache["initial_prompt_ids"] = str(initial_prompt_ids) if initial_prompt_ids is not None else None
        mc.cache["model"] = delegate.model_identifier
    
        mc.calls = 0
        mc.hits = 0

        mc.cache_file = cache_file

        try:
            if cache_file is not None and os.path.exists(cache_file):
                with open(cache_file, "rb") as f:
                    cache = pickle.load(f)
                    if cache["initial_prompt_ids"] != str(initial_prompt_ids):
                        print("warning: cache file is from a different query (revision). Its contents will be overwritten.")
                    elif cache["model"] != delegate.model_identifier:
                        print("warning: cache file is from a different model. Its contents will be overwritten.")
                    else:
                        mc.cache = cache
        except Exception as e:
            print("error: failed to load token cache from file", e)
            pass

        return mc
    
    def save(self):
        if self.cache_file is not None:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.cache, f)

    def base_id(self, s: DecoderSequence):
        return str(s.input_ids[self.input_id_key_offset:]) + "-" + (s.data("head").variable if s.data() is not None and "head" in s.data() else "None")

    async def rewrite(self, ar: Union[DataArray, List[DecoderSequence], DecoderSequence], noscore=False):
        return await self.delegate.rewrite(ar, noscore)

    async def get_mask(self, s: DecoderSequence, **kwargs):
        if s.id in self.mask_cache:
            return self.mask_cache[s.id]
        if hasattr(s, "logits_mask"):
            return s.logits_mask

        constrained_seqs = np.array([True], dtype=np.bool_)
        logits_mask_result = await self.delegate.compute_logits_mask(s.input_ids.reshape(1, -1), [s.user_data], constrained_seqs, [s], **kwargs)
        self.mask_cache[s.id] = logits_mask_result

        if s.user_data is None:
            s.user_data = {}
        s.user_data = deepmerge(deepcopy(s.user_data), logits_mask_result.user_data[0])
        s.user_data["set_by"] = "where"

        setattr(s, "logits_mask", logits_mask_result)

        return logits_mask_result

    async def get_cache(self, s: DecoderSequence, edge_type: str, **kwargs):
        kwargs = {**self.delegate.model_args, **kwargs}
        
        # standard key is sequence id + edge type
        keys = [(self.base_id(s), edge_type)] if edge_type != "sample" else []

        # compute logits mask
        mask = (await self.get_mask(s, **kwargs)).logits_mask[0]
        if mask is not None:
            if masks.mask_num_allowed(mask) == 1:
                keys.append((self.base_id(s), str(masks.mask_get_only_allowed(mask))))
            else:
                if masks.is_fixed_int_mask(mask):
                    keys.append((self.base_id(s), edge_type, hash("-".join([str(i) for i in mask]))))
                else:
                    keys.append((self.base_id(s), edge_type, hash("-".join([str(i) for i in np.where(mask >= 0)[0]]))))

        for k in keys:
            if k in self.cache:
                return keys, self.cache[k]

        return keys, None
    
    def set_cache(self, key, c: Union[Continuation, tuple]):
        for k in key:
            if type(c) is Continuation:
                self.cache[k] = (c.token, c.logprob)
            else:
                assert type(c) is tuple and len(c) == 2
                self.cache[k] = c

    async def argmax(self, arr: DataArray, **kwargs):
        async def op_argmax(seqs):
            self.calls += len(seqs)

            # check cache for all
            cache_entries = [await self.get_cache(s, 'top-1', **kwargs) for s in seqs]
            cached_tokens = [e[1] for e in cache_entries]
            cache_keys = [e[0] for e in cache_entries]
            
            # apply operation for non-cached
            non_cached = [s for s, c in zip(seqs, cached_tokens) if c is None]
            # generator over new results
            non_cached_argmax = iter((await self.delegate.argmax(DataArray(non_cached), **kwargs)).items())
            
            results = []
            # put new results in cache
            for i, (s, key, c) in enumerate(zip(seqs, cache_keys, cached_tokens)):
                if c is None: 
                    r = next(non_cached_argmax)
                    results.append(r)
                    self.set_cache(key, r)
                else:
                    token, logprob = c
                    user_data = (await self.get_mask(s, **kwargs)).user_data
                    continuation = s.make_successors(token.reshape(1), logprob, logits=None, user_data=user_data)
                    results.append(continuation)

                    self.hits += 1

            # read full result from cache
            return results

        return await arr.aelement_wise(op_argmax)

    async def sample(self, arr: DataArray, num_samples=1, **kwargs):
        async def op_sample(seqs):
            self.calls += len(seqs)

            # check cache for all
            cache_entries = [await self.get_cache(s, 'sample', **kwargs) for s in seqs]
            cached_tokens = [e[1] for e in cache_entries]
            cache_keys = [e[0] for e in cache_entries]
            
            # apply operation for non-cached
            non_cached = [s for s, c in zip(seqs, cached_tokens) if c is None]
            # generator over new results
            non_cached_sample = iter((await self.delegate.sample(DataArray(non_cached), num_samples=num_samples, **kwargs)).items())
            
            results = []
            # put new results in cache
            for i, (s, key, c) in enumerate(zip(seqs, cache_keys, cached_tokens)):
                if c is None: 
                    r = next(non_cached_sample)
                    results.append(r)
                    self.set_cache(key, r)
                else:
                    token, logprob = c
                    user_data = (await self.get_mask(s, **kwargs)).user_data
                    continuation = s.make_successors(token.reshape(1), logprob, logits=None, user_data=user_data)
                    results.append(continuation)
                    self.hits += 1

            # read full result from cache
            return results

        return await arr.aelement_wise(op_sample)

    async def topk_continuations(self, arr: DataArray, k: int, **kwargs):
        async def op_topk(seqs):
            self.calls += len(seqs)
            
            # check cache for all
            cache_entries_topk = [[] for s in seqs]
            for i in range(1, k+1):
                entries = [await self.get_cache(s, f'top-{i}', **kwargs) for s in seqs]
                for j, e in enumerate(entries):
                    cache_entries_topk[j].append(e)
            # per seq, top 1-k cached tokens 
            cached_tokens = [[e[1] for e in cache_entries] for cache_entries in cache_entries_topk]
            # per seq, top 1-k cache keys (multiple per entry)
            cache_keys = [[e[0] for e in cache_entries] for cache_entries in cache_entries_topk]

            # apply operation for non-cached
            non_cached = [s for s, c in zip(seqs, cached_tokens) if any(ct is None for ct in c)]
            # generator over new results
            non_cached_sample = iter((await self.delegate.topk_continuations(DataArray(non_cached), k=k, **kwargs)).items())
            
            results = []
            # put new results in cache
            for i, (s, key, c) in enumerate(zip(seqs, cache_keys, cached_tokens)):
                if any(ct is None for ct in c):
                    r = next(non_cached_sample)
                    results.append(r)
                    next_token_ids = ensure_iterable(r.token)
                    next_token_scores = ensure_iterable(r.logprob)
                    # cache each continuation separately
                    assert len(next_token_ids) <= len(key)
                    for i,ck in zip(range(len(next_token_ids)), key):
                        self.set_cache(ck, (next_token_ids[i], next_token_scores[i]))
                else:
                    assert len(c) == k, f"expected {k} cached tokens in topk_continuations, but got {len(c)}"
                    tokens = []
                    logprobs = []
                    user_data = []
                    for token, logprob in c:
                        c_user_data = (await self.get_mask(s, **kwargs)).user_data
                        continuation = s.make_successors(token.reshape(1), logprob.reshape(1), logits=None, user_data=c_user_data)
                        tokens.append(continuation.token)
                        logprobs.append(continuation.logprob)
                        user_data.append(continuation.user_data)
                    self.hits += 1
                    results.append(Continuation(np.array(tokens), np.array(logprobs), user_data))

            # read full result from cache
            return results

        return await arr.aelement_wise(op_topk)
    
    async def prescore(self, sqs: List[DecoderSequence], tokens: List[List[int]], max_batch_size=None, 
                    deterministic: Union[bool, List[bool]]=False, stop_phrase=False, needs_rewrite=True, 
                    user_data=None, noscore=False):
        async def op_score(sq, tok, max_batch_size, det, stop_phrase, needs_rewrite, user_data, noscore):
            assert len(user_data) == len(tok)

            while (self.base_id(sq), str(tok[0])) in self.cache:
                token, logprob = self.cache[(self.base_id(sq), str(tok[0]))]
                c = Continuation(token, logprob, user_data[0])
                sq = sq.extend(c, internal=True)
                tok = tok[1:]
                det = det[1:]
                user_data = user_data[1:]
                if len(tok) == 0:
                    return [sq]

            if len(tok) <= 1 and not noscore:
                return

            # # scoring is only necessary if there more than one token needs to be expanded
            # if len(tok) <= 1:
            #     return

            result = await self.delegate.score([sq], [tok], max_batch_size, det, stop_phrase, needs_rewrite, None, noscore, internal=True)

            # add initial cache entry
            s = result[0]
            s.user_data = user_data[0]
            c = Continuation(np.array([s.input_ids[-1]]), np.array([s.logprobs[-1]]), [user_data[0]])
            self.set_cache([(self.base_id(sq), str(int(s.input_ids[-1])))], c)
            user_data_offset = 1
            
            # add additional cache entries for deterministic tokens
            while type(s) is DeterministicDecoderSequence and len(s.next_ids) > 0:
                c = Continuation(np.array([s.next_ids[0]]), np.array([s.next_logprobs[0]]), [user_data[user_data_offset]])
                sq = s
                s = sq.extend(c)
                user_data_offset += 1
                self.set_cache([(self.base_id(sq), str(s.input_ids[-1]))], c)
        
        assert len(sqs) == len(tokens)
        return await asyncio.gather(*[op_score(sq, tok, max_batch_size, det, stop_phrase, needs_rewrite, ud, noscore) for sq, tok, det, ud in zip(sqs, tokens, deterministic, user_data)])
    
    @property
    def bos_token_id(self):
        return self.delegate.bos_token_id
    
    @property
    def eos_token_id(self):
        return self.delegate.eos_token_id
    
    @property
    def truncation_threshold(self):
        return self.delegate.truncation_threshold
    
    @property
    def model(self):
        return self.delegate.model
    
    def report_stats(self, *args):
        print("Cache hits: %d/%d (%.2f%%)" % (self.hits, self.calls, 100 * self.hits / max(1,self.calls)))

        return self.delegate.report_stats(*args)
    
    def log_billable_tokens(self, *args, **kwargs):
        return self.delegate.log_billable_tokens(*args, **kwargs)
    
    async def tokenize(self, *args, **kwargs):
        return await self.delegate.tokenize(*args, **kwargs)
    
    async def detokenize(self, *args, **kwargs):
        return await self.delegate.detokenize(*args, **kwargs)

    def log_queries(self, n: int):
        return self.delegate.log_queries(n)
    
    async def score(self, *args, **kwargs):
        # make use of self.cache during scoring
        return await self.delegate.score(*args, **kwargs)