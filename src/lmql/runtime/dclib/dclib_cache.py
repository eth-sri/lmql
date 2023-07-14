import asyncio
from lmql.runtime.dclib.dclib_seq import DecoderSequence
import numpy as np
import pickle
import os
from typing import List, Union, Any
from dataclasses import dataclass

from .dclib_array import DataArray
from .dclib_seq import DecoderSequence, Continuation, DeterministicDecoderSequence, deepcopy, deepmerge, detseq
from .dclib_model import DcModel, CacheDelegate
from .dclib_rewrite import DcModelRewriteMixin
import lmql.runtime.masks as masks
from lmql.utils.nputil import ensure_iterable
from concurrent.futures import ThreadPoolExecutor

class CacheFile:
    def __init__(self, filename, initial_ids, model):
        self.filename = filename
        self.initial_ids = initial_ids
        self.model = model
    
    def load(self):
        if self.filename is not None and os.path.exists(self.filename):
            with open(self.filename, "rb") as f:
                cache = pickle.load(f)
                if cache.get("model") != self.model:
                    print("warning: cache file is from a different model. Its contents will be overwritten. {} != {}".format(cache["model"], self.model))
                else:
                    return cache.get(str(self.initial_ids), {})
        return {}
    
    def save(self, cache):
        if os.path.exists(self.filename):
            with open(self.filename, "rb") as f:
                existing_cache = pickle.load(f)
                if existing_cache.get("model") != self.model:
                    print("warning: cache file is from a different model. Its contents will be overwritten. {} != {}".format(cache.get("model"), self.model))
                    existing_cache = {}
        else:
            existing_cache = {}
        if "model" in existing_cache.keys() and existing_cache["model"] != self.model:
            print("warning: cache file is from a different model. Its contents will be overwritten. {} != {}".format(existing_cache.get("model"), self.model))
            existing_cache = {}
        existing_cache["model"] = self.model
        existing_cache[str(self.initial_ids)] = cache
        
        with open(self.filename, "wb") as f:
            pickle.dump(existing_cache, f)


class CachedDcModel(DcModelRewriteMixin, CacheDelegate):
    delegate: DcModel
    
    def __new__(cls, delegate: DcModel, initial_prompt_ids=None, cache_file=None, show_speculative=False):
        mc = super().__new__(cls)
        
        mc.delegate: DcModel = delegate

        # setup cache delegate
        assert delegate.cache_delegate is None, "cannot cache a model that is already cached by another cache_delegate"
        delegate.cache_delegate = mc

        mc.token_streams = []
        
        mc.cache = {}
        mc.user_data_cache = {}
        mc.cache_lock = asyncio.Lock()

        mc.mask_cache = {}
        mc.show_speculative = show_speculative
        mc.initial_ids = initial_prompt_ids
        
        mc.input_id_key_offset = len(initial_prompt_ids) if initial_prompt_ids else 0
        mc.initial_prompt_ids = initial_prompt_ids
        mc.cache["model"] = delegate.model_identifier
    
        mc.calls = 0
        mc.hits = 0

        mc.cache_file = cache_file

        try:
            mc.cache = CacheFile(cache_file, initial_prompt_ids, delegate.model_identifier).load()
        except Exception as e:
            print("error: failed to load token cache from file", e)
            pass

        return mc
    
    @property
    def tokenizer(self):
        return self.delegate.tokenizer

    def close(self):
        if self.cache_file is not None:
            cf = CacheFile(self.cache_file, self.initial_ids, self.delegate.model_identifier)
            try:
                cf.save(self.cache)
            except Exception as e:
                print("error: failed to save token cache to file", e, flush=True)
                pass

        self.model.cache_delegate = None
        for ts in self.token_streams:
            ts.cancel()
        self.token_streams = []

        if hasattr(self.delegate, "close"):
            self.delegate.close()
    
    def base_key(self, ids, *args):
        if isinstance(ids, DecoderSequence):
            return self.base_key(ids.input_ids)
        return "[" + ",".join([str(i) for i in ids]) + "]"

    async def get_mask(self, s: DecoderSequence, **kwargs):
        if s.id in self.mask_cache:
            return self.mask_cache[s.id]
        if hasattr(s, "logits_mask"):
            return s.logits_mask

        constrained_seqs = np.array([True], dtype=np.bool_)
        logits_mask_result = await self.delegate.compute_logits_mask(s.input_ids.reshape(1, -1), [s.user_data], constrained_seqs, [s], **kwargs, required=True)
        self.mask_cache[s.id] = logits_mask_result

        if s.user_data is None:
            s.user_data = {}
        s.user_data = deepmerge(deepcopy(s.user_data), logits_mask_result.user_data[0])
        s.user_data["set_by"] = "where"

        setattr(s, "logits_mask", logits_mask_result)

        return logits_mask_result

    async def get_keys(self, s: DecoderSequence, edge_type: str, **kwargs):
        kwargs = {**self.delegate.model_args, **kwargs}

        keys = []

        # compute logits mask
        mask = (await self.get_mask(s, **kwargs)).logits_mask[0]

        if type(s) is DeterministicDecoderSequence and len(s.next_ids) > 0:
            keys.append((self.base_key(s), str(s.next_ids[0])))

        if mask is not None:
            if masks.mask_num_allowed(mask) == 1:
                keys.append((self.base_key(s), str(masks.mask_get_only_allowed(mask))))
            else:
                if masks.is_fixed_int_mask(mask):
                    keys.append((self.base_key(s), edge_type, "-".join([str(i) for i in mask])))

                    if edge_type == "top-1":
                        argmax_token, argmax_score = self.cache.get((self.base_key(s), "top-1"), (None, None))
                        if type(argmax_token) is int and argmax_token in mask:
                            keys.append((self.base_key(s), str(argmax_token)))
                else:
                    keys.append((self.base_key(s), edge_type, "-".join([str(i) for i in np.where(mask >= 0)[0]])))
        else:
            # standard key is sequence id + edge type
            keys.append((self.base_key(s), edge_type))

        return keys
    
    async def get_cache(self, s: DecoderSequence, edge_type: str, user_data=False, **kwargs):
        keys = await self.get_keys(s, edge_type, **kwargs)

        for k in keys:
            token, score = None, None
            
            async with self.cache_lock:
                if k in self.cache:
                    token, score = self.cache[k]
            
            if token is None:
                continue

            if type(token) is asyncio.Future: 
                awaited_result = await token
                if awaited_result is None:
                    continue
                else:
                    assert type(awaited_result) is tuple and len(awaited_result) == 2
                    token, score = awaited_result
            if user_data:
                return keys, (token, score, self.user_data_cache.get(k, None))
            return keys, (token, score)

        return keys, None
    
    def set_cache(self, key, c: Union[Continuation, tuple], user_data=None, verbose=False):
        for k in key:
            if verbose:
                print("    cached", k)
            
            # check if the existing entry is a future
            existing = self.cache.get(k, (None, None))[0]
            fut = existing if type(existing) is asyncio.Future else None
            
            if type(c) is Continuation:
                self.cache[k] = (c.token, c.logprob)
                if user_data is not None:
                    self.user_data_cache[k] = user_data
                if fut is not None and not fut.done():
                    fut.set_result((c.token, c.logprob))
            else:
                assert type(c) is tuple and len(c) == 2
                self.cache[k] = c
                if user_data is not None:
                    self.user_data_cache[k] = user_data
                if fut is not None and not fut.done():
                    fut.set_result(c)

    async def argmax(self, arr: DataArray, **kwargs):
        async def op_argmax(seqs):
            self.calls += len(seqs)

            # check cache for all
            cache_entries = [await self.get_cache(s, 'top-1', user_data=True, **kwargs) for s in seqs]
            cached_tokens = [e[1] for e in cache_entries]
            cache_keys = [e[0] for e in cache_entries]

            # apply operation for non-cached
            non_cached = [s for s, c in zip(seqs, cached_tokens) if c is None]
            # if len(non_cached) == 0:
            #     print("cache hit for", len(cache_keys[0][0][0]), cache_keys[0][0][0][-50:], "with", cached_tokens[0][0])
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
                    token, logprob, cached_user_data = c
                    logit_mask_result = await self.get_mask(s, **kwargs)
                    user_data = deepmerge(logit_mask_result.user_data[0], cached_user_data) if cached_user_data is not None else logit_mask_result.user_data[0]
                    continuation = s.make_successors(token.reshape(1), logprob.reshape(1), logits=None, user_data=[user_data])
                    results.append(continuation)

                    self.hits += 1

            # read full result from cache
            return results

        return await arr.aelement_wise(op_argmax)

    async def sample(self, arr: DataArray, num_samples=1, **kwargs):
        async def op_sample(seqs):
            self.calls += len(seqs)

            # check cache for all
            temperature = kwargs.get('temperature', 1.0)
            sampling_mode = "top-1" if temperature == 0.0 else "sample-{}".format(temperature)
            
            cache_entries = [await self.get_cache(s, sampling_mode, **kwargs) for s in seqs]
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
            
            # construct possible cache entries for all seqs (min(k, num_possible))
            cache_entries_topk = [] 
            for s in seqs:
                max_k = k
                if type(s) is DeterministicDecoderSequence and len(s.next_ids) > 0:
                    max_k = 1
                mask = await self.get_mask(s, **kwargs)
                if mask is not None:
                    mask = mask.logits_mask[0]
                    if mask is not None:
                        max_k = min(k, masks.mask_num_allowed(mask))
                cache_entries_topk.append([await self.get_cache(s, f'top-{i}', **kwargs) for i in range(1, max_k+1)])

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
                    if any(ct is not None for ct in c):
                        mask = (await self.get_mask(s, **kwargs)).logits_mask[0]
                        # print("WARNING: some cache entries are None, but some are not", len([e for e in c if e is not None]), len(r.token))
                        # print([await s.text()])
                    results.append(r)
                    next_token_ids = ensure_iterable(r.token)[:len(key)]
                    next_token_scores = ensure_iterable(r.logprob)[:len(key)]

                    # cache each continuation separately
                    assert len(next_token_ids) <= len(key)
                    for i,ck in zip(range(len(next_token_ids)), key):
                        self.set_cache(ck, (next_token_ids[i], next_token_scores[i]))
                    
                    # fill remaining top-k slots with empty result
                    for i in range(len(next_token_ids) + 1, k + 1):
                        self.set_cache([(self.base_key(s), "top-{}".format(i))], (None, None))
                else:
                    tokens = []
                    logprobs = []
                    user_data = []
                    for token, logprob in c:
                        if token is None and logprob is None:
                            # empty cache slot (top-i is not possible due to masking or truncation)
                            continue
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
    
    def expand_through_cache(self, sq: DecoderSequence, tok: List[int], det: List[bool], user_data: List[Any], initial_user_data=None):
        """
        Steps along the cache based on 'tok' until no more cache entries are found.
        """
        while (self.base_key(sq), str(tok[0])) in self.cache.keys():
            token, logprob = self.cache[(self.base_key(sq), str(tok[0]))]
            c = Continuation(token, logprob, user_data[0])
            sq = sq.extend(c, internal=True)
            tok = tok[1:]
            if type(det) is not bool:
                det = det[1:]
            user_data = user_data[1:]
            if len(tok) == 0:
                return sq, tok, det, user_data
        return sq, tok, det, user_data

    async def prescore_tokens(self, sq: DecoderSequence, tok: List[int], noscore=False):
        user_data = sq.user_data

        # expand through cache
        while (self.base_key(sq), str(tok[0])) in self.cache.keys():
            token, logprob = self.cache[(self.base_key(sq), str(tok[0]))]
            c = Continuation(token, logprob, sq.user_data)
            sq = sq.extend(c, internal=True)
            tok = tok[1:]
            if len(tok) == 0:
                break

        if len(tok) == 0: return
        # do actual scoring with delegate model
        self.calls += 1
        sq, tokens, scores = await anext(self.delegate.score_tokens([sq], [tok], noscore=noscore))
        self.save_cached(sq.input_ids, tokens, scores, user_data)
        
    def save_cached(self, ids: List[bytes], tokens, scores, user_data):
        # add cache entries along pre-scored trajectory
        for tok, score in zip(tokens, scores):
            value = (np.array(tok).reshape(1), np.array(score).reshape(1))
            self.set_cache([(self.base_key(ids, user_data), tok)], value)
            ids = np.append(ids, tok)

    @property
    def model_args(self):
        return self.delegate.model_args

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
        # print("Cache hits: %d/%d (%.2f%%)" % (self.hits, self.calls, 100 * self.hits / max(1,self.calls)))
        return self.delegate.report_stats(*args)
    
    def log_billable_tokens(self, *args, **kwargs):
        return self.delegate.log_billable_tokens(*args, **kwargs)
    
    async def tokenize(self, *args, **kwargs):
        return await self.delegate.tokenize(*args, **kwargs)
    
    async def detokenize(self, *args, **kwargs):
        return await self.delegate.detokenize(*args, **kwargs)

    def log_queries(self, n: int):
        return self.delegate.log_queries(n)
    
    async def score(self, sqs: List[DecoderSequence], tokens: List[List[int]], max_batch_size=None, deterministic: Union[bool, List[bool]]=False, stop_phrase=False, needs_rewrite=True, user_data=None, noscore=False, internal=False):
        async def op_score(sq, tok):
            unexpanded_tok = tok
            # create continuation sequence at cache boundary
            continued_seq, tok, det, _ = self.expand_through_cache(sq, tok, deterministic, [user_data for _ in tok])

            if len(tok) == 0:
                completion = np.array(unexpanded_tok)
                token_scores = continued_seq.logprobs[-len(completion):]
            else:
                self.calls += 1
                # run actual score() call for remaining non-cached part of 'tokens' (tok)
                result: DeterministicDecoderSequence = (await self.delegate.score([continued_seq], [tok], max_batch_size, det, stop_phrase, needs_rewrite=needs_rewrite, user_data=user_data, noscore=noscore, internal=True))[0]
                
                # extract scores and tokens for new, scored part of 'tokens'
                token_scores = np.array(result.logprobs[len(sq.input_ids):].tolist() + result.next_logprobs.tolist())
                completion = np.array(unexpanded_tok)
                assert len(token_scores) == len(completion), f"Expected {len(completion)} scores, but got {len(token_scores)}"

                # store in cache
                ids = continued_seq.input_ids
                for i, (score, token) in enumerate(zip(token_scores[-len(tok):], tok)):
                    self.set_cache([(self.base_key(ids), str(token))], (np.array(token), np.array(score)))
                    ids = np.append(ids, token)
                
            # determine detseq deterministic flags
            if type(deterministic) is bool:
                deterministic_flags = np.concatenate([sq.deterministic, np.array([deterministic])], dtype=np.bool_)
                next_deterministic = np.array([deterministic] * len(completion[1:]))
            else:
                assert type(deterministic) is list and len(deterministic) == len(completion), "If deterministic is a list, it must have the same length as the number of tokens to be scored, but is {} and {}".format(deterministic, completion)
                deterministic_flags = np.concatenate([sq.deterministic, np.array(deterministic[:1])], dtype=np.bool_)
                next_deterministic = np.array(deterministic[1:])

            # create actual detseq
            return detseq(ids=np.concatenate([sq.input_ids, completion[:1]], axis=0), 
                    next_ids=completion[1:],
                    logprobs=np.concatenate([sq.logprobs, token_scores[:1]], axis=0),
                    next_logprobs=token_scores[1:],
                    deterministic=deterministic_flags,
                    next_deterministic=next_deterministic,
                    predecessor=sq,
                    user_data=user_data,
                    stop_phrase=np.concatenate([sq.stop_phrase, np.array([stop_phrase])]),
                    needs_rewrite=needs_rewrite,
                    sticky_user_data_keys=sq.sticky_user_data_keys,
                    internal=internal
            )
        return await asyncio.gather(*[op_score(sq, tok) for sq, tok in zip(sqs, tokens)])

    def register_token_stream(self, token_iterator: callable):
        async def token_consumer(itr):
            try:
                ids = None
                keys = None
                sq = None
                waiting_token_keys = []

                async for (s, tokens, scores, edge_types, user_data) in itr():
                    async with self.cache_lock:
                        if type(tokens) is int or len(tokens) == 1:
                            tokens = ensure_iterable(tokens)
                            scores = ensure_iterable(scores)
                            if type(edge_types) is str or edge_types is None:
                                edge_types = [edge_types]
                        else:
                            assert len(tokens) == len(scores) == len(edge_types), f"token_consumer: expected all lists to have the same length, but got {len(tokens)}, {len(scores)}, {len(edge_type)}"
                            # print("setting entries for", edge_types)
                        
                        waiting_token_keys = []
                        
                        for token, score, edge_type in reversed(list(zip(tokens, scores, edge_types))):
                            assert type(edge_type) is str or edge_type is None, "edge_types is {}".format(edge_types)

                            if ids is None:
                                ids = s.input_ids
                                keys = await self.get_keys(s, edge_type, **self.model_args)
                                sq = s
                            
                            token_keys = [(self.base_key(ids), edge_type, *k[2:]) for k in keys]
                            token_keys += [(self.base_key(ids), str(token))]
                            # filter out keys with edge_type=None
                            token_keys = [k for k in token_keys if k[1] is not None]

                            # for tk in token_keys:
                            #     if tk in self.cache and type(self.cache[tk][0]) is not asyncio.Future:
                            #         print("token_consumer: token for {} from stream already in cache ({} streams): {}".format(tk, len(self.token_streams), self.cache[tk]))

                            self.set_cache(token_keys, (np.array(token).reshape(1), np.array(score).reshape(1)), user_data=user_data, verbose=False)

                            if self.show_speculative:
                                c = Continuation(np.array(token), np.array(score), None)
                                cs = sq.extend(c)
                                if edge_type == "top-1":
                                    sq = cs

                            if edge_type is not None and (edge_type == "top-1" or "top" not in edge_type):
                                # set future for next token (so get_cache can wait for it if needed)
                                fut_keys = [(self.base_key(np.append(ids, token)), edge_type, *k[2:]) for k in keys]
                                waiting_token_keys.append(fut_keys)
                                # set future for next token (if k is not already set)
                                fut = asyncio.Future()
                                unset_keys = [k for k in fut_keys if k not in self.cache]
                                self.set_cache(unset_keys, (fut, fut))
                        
                        # extend ids
                        ids = np.append(ids, tokens[0])

                # remove last waiting token entry (since it will not be provided by this stream)
                for future_keys in waiting_token_keys:
                    for k in future_keys:
                        fut = self.cache.get(k, (None, None))[0]
                        if type(fut) is asyncio.Future:
                            # resolve future as invalid (handled in get_cache)
                            fut.set_result(None)
                            del self.cache[k]
            except Exception as e:
                print("DcCachedModel: token_consumer failed with:", e)
                import traceback
                traceback.print_exc()
                raise e

        self.token_streams = [s for s in self.token_streams if not s.done()]

        task = token_consumer(token_iterator)
        self.token_streams.append(asyncio.ensure_future(task))
        
    async def wait_for_active_streams(self):
        """
        Waits until all active cache streams have been processed.
        """
        caches = self.token_streams
        # remove all done cache streams
        self.token_streams = [f for f in self.token_streams if not f.done()]
        return await asyncio.gather(*caches)
