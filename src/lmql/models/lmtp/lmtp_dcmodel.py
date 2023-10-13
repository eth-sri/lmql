"""
LMQL model implementation that uses the LMTP protocol to communicate with a
hosted model server, or a model running in a separate process.
"""

from lmql.runtime.dclib.dclib_model import DcModel
from lmql.runtime.tokenizer import tokenizer
from .lmtp_async import LMTPAsyncClient
import lmql.runtime.dclib as dc
import asyncio
import numpy as np
import lmql.utils.nputil as nputil
import lmql.runtime.masks as masks
from lmql.runtime.tracing import active_tracer, Event
from lmql.runtime.token_distribution import TokenDistribution
from lmql.api.llm import ModelAPIAdapter

from typing import Any, List, Union, Type
import random
import sys
import traceback

class LMTPDcModel(DcModel):
    def __init__(self, model, tokenizer, endpoint, inprocess=False, truncation_threshold=-3e38, init_workers=True, lmtp_server_kwargs=None, inprocess_client_constructor=None, verbose=False, **kwargs):
        super().__init__(model, tokenizer, truncation_threshold, init_workers, **kwargs)

        self.model.chunk_size = kwargs.get("chunksize", 16)

        # LMTP client object (can be inprocess, websocket, or an alternative like replicate)
        self.client = None
        # model info as advertised by inference endpoint
        self._model_info = None
        # asyncio task for client loop
        self._client_loop = None
        # set once self.client is set up
        self.connected_signal = asyncio.Event()
        # set to termiante self._client_loop
        self.close_signal = asyncio.Event()
        # error signal
        self.error_signal = asyncio.Event()
        self.error = None

        # verbose logging
        self.verbose = verbose

        # endpoint in case of remote model
        self.endpoint = endpoint
        self.use_replicate = False
        if endpoint is None:
            pass
        elif endpoint.startswith('replicate:') or endpoint == 'replicate':
            self.use_replicate = True
        elif not self.endpoint.startswith("http"):
            self.endpoint = "http://" + self.endpoint

        self.inprocess = inprocess
        self.lmtp_server_kwargs = lmtp_server_kwargs
        assert self.inprocess or  lmtp_server_kwargs is None, "LMTP server kwargs can only be set when using lmql.inprocess mode"
        if inprocess:
            self.inprocess_client_constructor = inprocess_client_constructor

        EXTRA_DECODING_PARAMETERS = ["top_p", "top_k", "repetition_penalty", "presence_penalty", "length_penalty", "frequency_penalty"]
        # API decoding parameters
        self.extra_decoding_parameters = {
            **{p: kwargs[p] for p in EXTRA_DECODING_PARAMETERS if p in kwargs}
        }

        # model statistics
        self.requests = 0
        self.tokens = 0

    async def inprocess_client_loop(self):
        self.client = self.inprocess_client_constructor(self.model.model_identifier, **self.lmtp_server_kwargs)

        self.connected_signal.set()
        await self.close_signal.wait()
        await self.client.close()
        self.client = None

    async def replicate_client_loop(self):
        try:
            import aiohttp
            from .lmtp_replicate_client import LMTPReplicateClient
            async with aiohttp.ClientSession() as session:
                self.client = LMTPReplicateClient(self.model.model_identifier, session, self.endpoint,
                    **(self.lmtp_server_kwargs or {})
                )
                await self.client.check_model()
                self.connected_signal.set()
                await self.close_signal.wait()
        except Exception as e:
            self.error_signal.set()
            self.error = str(e)
            self.connected_signal.set()
            print("Failed to initial replicate.com connection:", e, flush=True)

    async def ws_client_loop(self):
        import aiohttp
        from .lmtp_client import LMTPWebSocketClient

        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.endpoint) as ws:
                    self.client = LMTPWebSocketClient(self.model.model_identifier, ws)
                    self.client.connect()
                    
                    self.connected_signal.set()
                    await self.close_signal.wait()
        except Exception as e:
            self.error_signal.set()
            self.error = f"Exception {e!s} attempting to communicate with lmtp endpoint: {self.endpoint!s}. Please check that the endpoint is correct and the server is running."
            self.connected_signal.set()
            traceback.print_tb(e.__traceback__)

    def make_cache_entry(self, s, payload, sampling_mode):
        scores = {}
        for t, score in payload["top_logprobs"].items():
            scores[int(t)] = score
        
        if sampling_mode == "top-1":
            scores[int(payload["token"])] = payload["logprob"]

        top_entries = list(sorted(scores.items(), key=lambda x: x[1], reverse=True))
        tokens = [t for t, _ in top_entries]
        scores = [s for _, s in top_entries]
        edge_type = ["top-{}".format(i+1) for i in range(len(top_entries))]

        # for non argmax sampling modes, add the sampled token
        if sampling_mode != "top-1":
            tokens = [payload["token"]] + tokens
            scores = [payload["logprob"]] + scores
            edge_type = [sampling_mode] + edge_type

        tokens = self.tokenizer.decode_bytes(tokens)

        # replace top-1 with payload["token"] if sampling mode is top-1
        if sampling_mode == "top-1":
            edge_type[0] = "top-1"
            tokens[0] = self.tokenizer.decode_bytes([payload["token"]])

        return (s, tokens, scores, edge_type, {})

    async def stream_and_return_first(self, s, iterator, sampling_mode):
        buffer = []
        for i in range(4):
            try:
                buffer += [await anext(iterator)]
            except StopAsyncIteration:
                break
        self.requests += 1

        async def token_stream():
            nonlocal buffer

            self.tokens += 1
            
            for item in buffer:
                yield self.make_cache_entry(s, item, sampling_mode)

            while True:
                try:
                    self.tokens += 1
                    item = await anext(iterator)
                    yield self.make_cache_entry(s, item, sampling_mode)
                except StopAsyncIteration:
                    is_done = True
                    break
        
        async def do_register():
            self.register_token_stream(token_stream)
        asyncio.ensure_future(do_register())
        
        return buffer[0]

    async def ensure_connected(self):
        if self.error_signal.is_set():
            raise RuntimeError("LMTP client encountered an error: {}".format(self.error))

        if self.client is None:
            if self._client_loop is None:
                if self.inprocess:
                    self._client_loop = asyncio.create_task(self.inprocess_client_loop(), name="lmtp_inprocess_client_loop")
                elif self.use_replicate:
                    self._client_loop = asyncio.create_task(self.replicate_client_loop(), name="lmtp_replicate_client_loop")
                else:
                    self._client_loop = asyncio.create_task(self.ws_client_loop(), name="lmtp_ws_client_loop")
        
        await self.connected_signal.wait()
        
        # double check for errors
        if self.error_signal.is_set():
            raise RuntimeError("LMTP client encountered an error: {}".format(self.error))

    # on deinit
    def close(self):
        self.close_signal.set()
        if self._client_loop is not None:
            self._client_loop.cancel()

    def __del__(self):
        self.close_signal.set()
        if self._client_loop is not None:
            self._client_loop.cancel()

    async def model_info(self):
        if self._model_info is None or self._model_info == "<unavailable>":
            self._model_info = (await self.client.request("MODEL_INFO", {
                "model": self.model_identifier
            }))["model_info"]
        return self._model_info

    def make_logits(self, payload):
        scores = {}
        for t, score in payload["top_logprobs"].items():
            scores[int(t)] = score
        scores[int(payload["token"])] = payload["logprob"]
        scores = scores.items()

        logits = TokenDistribution()
        logits[[t for t, _ in scores]] = [s for _, s in scores]

        return logits

    async def singleton_result(self, token, score):
        yield {"token": token, "logprob": score, "top_logprobs": {token: score}}

    async def generate(self, s, temperature, top_logprobs = 1, chunk_size=None, **kwargs):
        if chunk_size is None:
            chunk_size = self.model.chunk_size
        kwargs = {**self.model_args, **kwargs}

        # get token masks from interpreter
        constrained_seqs = np.array([s.is_query_constrained], dtype=np.bool_)
        logits_mask_result = await self.compute_logits_mask(s.input_ids.reshape(1, -1), [s.user_data], constrained_seqs, [s], **kwargs)
        mask = logits_mask_result.logits_mask[0]
        
        assert kwargs.get("num_samples", 1) == 1, "LMTP does not support num_samples > 1 right now. Please, duplicate your dc.seq to obtain multiple sampled continuations."

        # merge interpreter user data with previous/decoder data
        if s.user_data is None:
            s.user_data = {}
        s.user_data = dc.deepmerge(dc.deepcopy(s.user_data), logits_mask_result.user_data[0])
        s.user_data["set_by"] = "where"

        # convert token mask to LMTP format
        if mask is not None:
            num_allowed = masks.mask_num_allowed(mask)
            if num_allowed == 1:
                only_allowed_id = masks.mask_get_only_allowed(mask)
                return self.singleton_result(only_allowed_id, 0.0)
            
            assert nputil.is_array(mask), "logit_mask_or_fixed_id must be a LongTensor not a " + str(type(mask))
            invert = num_allowed < self.tokenizer.vocab_size - num_allowed

            if invert: masked = (mask >= 0)
            else: masked = (mask < 0)
            mask_value = 100 if invert else -100
            mask = {int(idx): mask_value for idx in np.nonzero(masked)[0]}

        # convert seq to input IDs
        ids = self.tokenizer.convert_bytes_to_ids(s.input_ids)
        
        if len(ids) == 0 or (len(ids) > 0 and self.tokenizer.bos_token_id is not None and ids[0] != self.tokenizer.bos_token_id):
            ids = [self.tokenizer.bos_token_id] + ids
        
        # derive max_tokens
        max_tokens = logits_mask_result.max_tokens_hints[0] or chunk_size
        # if '-1', generation is not limited
        if max_tokens == -1: max_tokens = 128

        if self.verbose:
            text = await self.detokenize(ids)
            print("lmtp generate: {} / {} ({} tokens, temperature={}, max_tokens={})".format(ids, str([text])[1:-1], len(ids), temperature, max_tokens))

        # get token stream
        token_stream = self.client.generate(ids, max_tokens=max_tokens, temperature=temperature, logit_bias=mask, top_logprobs=top_logprobs, **self.extra_decoding_parameters)
        
        if active_tracer().active:
            stream_event = active_tracer().event("lmtp.generate", {
                "model": await self.model_info(),
                "tokenizer": str(self.tokenizer),
                "kwargs": {
                    "ids": ids,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    **({"logit_bias": mask} if mask is not None else {}),
                    "top_logprobs": top_logprobs,
                    **self.extra_decoding_parameters
                }
            })

            return self.traced_generate(token_stream, event=stream_event)

        return token_stream

    async def traced_generate(self, generate_iterator, event: Event):
        first = True
        async for item in generate_iterator:
            if first:
                event.update({"model": await self.model_info()})
                first = False
            
            event.add("result", [item["token"]])
            yield item

    async def argmax(self, sequences: dc.DataArray, **kwargs):
        return await self.sample(sequences, temperature=0.0, **kwargs)

    async def sample(self, sequences: dc.DataArray, temperature, **kwargs):
        await self.ensure_connected()
        
        sampling_mode = "top-1" if temperature == 0.0 else "sample-{}".format(temperature)

        assert kwargs.get("num_samples", 1) == 1, "LMTPDcModel does not support num_samples != 1"

        async def op_sample(seqs):
            if len(seqs) == 0:
                return []
            
            if all(type(s) is dc.DeterministicDecoderSequence for s in seqs) and all(len(s.next_ids) > 0 for s in seqs):
                next_token_ids = np.array([s.next_ids[0] for s in seqs])
                next_token_scores = np.array([s.next_logprobs[0] for s in seqs])
                next_token_ids = np.array([self.tokenizer.decode_bytes([t])[0] for t in next_token_ids])
                return [s.make_successors(next_token_ids[i].reshape(1), next_token_scores[i], logits=None) for i,s in enumerate(seqs)]
            
            self.model.num_queries += len(seqs)

            # by default we do not need to store any user data in continuations
            user_data = [None for _ in seqs]

            # if sampling freshly, generate a new sample id to identify the full sampled sequence in the cache
            if temperature > 0.0:
                unique_sampling_mode = [f"{sampling_mode}-sample-id-{random.randint(0, 2**32-1)}" for _ in seqs]
                # store sample-unique id per continuation
                user_data = [[{"dc-edge-type": mode}] for mode in unique_sampling_mode]
            else:
                # no sample-id needed for (deterministic) top-1
                unique_sampling_mode = [sampling_mode for _ in seqs]

            tokens = await asyncio.gather(*[self.stream_and_return_first(s, await self.generate(s, temperature=temperature, **kwargs), mode) for s,mode in zip(seqs, unique_sampling_mode)])

            next_token_ids = np.array([t['token'] for t in tokens], dtype=np.int64)
            next_token_scores = np.array([t['logprob'] for t in tokens], dtype=np.float32)
            next_logits = [self.make_logits(t) for t in tokens]

            next_tokens = np.array([self.tokenizer.decode_bytes([t])[0] for t in next_token_ids])

            return [s.make_successors(next_tokens[i].reshape(1), next_token_scores[i], logits=next_logits[i], user_data=user_data[i]) for i,s in enumerate(seqs)]
        
        return await sequences.aelement_wise(op_sample)

    async def topk_continuations(self, sequences, k, **kwargs):
        await self.ensure_connected()

        kwargs = {**self.model_args, **kwargs}

        async def op_topk(seqs, k):
            if len(seqs) == 0:
                return []

            if all(type(s) is dc.DeterministicDecoderSequence for s in seqs) and all(len(s.next_ids) > 0 for s in seqs):
                next_token_ids = np.array([s.next_ids[0] for s in seqs])
                next_token_scores = np.array([s.next_logprobs[0] for s in seqs])
                next_token_ids = np.array([self.tokenizer.decode_bytes([t])[0] for t in next_token_ids])
                return [s.make_successors(next_token_ids[i].reshape(1), next_token_scores[i], logits=None) for i,s in enumerate(seqs)]

            self.model.num_queries += len(seqs)
            result = await asyncio.gather(*[self.stream_and_return_first(s, await self.generate(s, temperature=0.0, top_logprobs=k, chunk_size=None if k == 1 else 1, **kwargs), "top-1") for s in seqs])

            logits = []
            next_token_ids = []
            next_token_scores = []

            for i, s in enumerate(seqs):
                # prepare distribution
                distribution = TokenDistribution()
                logprob_items = result[i]["top_logprobs"].items()
                
                logprobs = [logprob for _, logprob in logprob_items]
                tokens = [int(token) for token, _ in logprob_items]                
                chosen_token = result[i]["token"]
                chosen_logprob = result[i]["logprob"]
                tokens += [chosen_token]
                logprobs += [chosen_logprob]
                
                tokens = np.array([self.tokenizer.decode_bytes([t])[0] for t in tokens])

                distribution[tokens] = logprobs

                # make sure all token_ids are unique
                tokens = np.array(list(set(tokens)))

                tokens, logprobs = distribution.topk(k)

                next_token_ids.append(tokens)
                next_token_scores.append(logprobs)
                logits.append(distribution)

            return [s.make_successors(next_token_ids[i], next_token_scores[i], logits=logits[i], user_data=None) for i,s in enumerate(seqs)]

        return await sequences.aelement_wise(op_topk, k=k)

    def report_stats(self, printer, decoder_step=None):
        if printer is None:
            return
        if hasattr(printer, "report_model_stats"):
            data = {
                "tokens": self.tokens,
                "model": self.model_identifier,
                "req.": self.requests,
                "avb": 0,
            }
            if decoder_step is not None:
                data["_step"] = decoder_step
            printer.report_model_stats(**data)

    async def _score_next_tokens(self, s, next_tokens, noscore=False):
        if noscore:
            return np.zeros(len(next_tokens), dtype=np.float32)
    
        await self.ensure_connected()
        
        scores = []
        i = 0
        
        ids = self.tokenizer.convert_bytes_to_ids(s.input_ids)
        next_tokens = self.tokenizer.convert_bytes_to_ids(next_tokens)

        if self.tokenizer.bos_token_id is not None and (len(ids) == 0 or ids[0] != self.tokenizer.bos_token_id):
            ids = [self.tokenizer.bos_token_id] + ids

        if self.verbose:
            text = await self.detokenize(ids)
            next_texts = await self.detokenize(next_tokens)
            print("lmtp score: {} + {} / {} + {} ({} tokens)".format(ids, next_tokens, str([text])[1:-1], str([next_texts])[1:-1], len(ids)))

        async for token in self.client.score(ids, next_tokens):
            t = next_tokens[i]
            assert token["token"] == t, "Expected token {}, got {}".format(t, token["token"])
            scores.append(token["logprob"])
            i += 1
        assert len(scores) == len(next_tokens), "Expected {} scores, got {}".format(len(next_tokens), len(scores))
        
        return np.array(scores, dtype=np.float32)
    
    async def score(self, sqs: List[dc.DecoderSequence], tokens: List[List[int]], max_batch_size=4, deterministic: Union[bool, List[bool]]=False, stop_phrase=False, needs_rewrite=True, user_data=None, noscore=False, internal=False):
        await self.ensure_connected()
        
        assert len(sqs) == len(tokens), "Number of sequences and number of tokens to be scored must match, but got {} and {}".format(len(sqs), len(tokens))

        def make_detseq(s, token_score, completion):
            # compose deterministic flags
            if type(deterministic) is bool:
                deterministic_flags = np.concatenate([s.deterministic, np.array([deterministic])], dtype=np.bool_)
                next_deterministic = np.array([deterministic] * len(completion[1:]))
            else:
                assert type(deterministic) is list and len(deterministic) == len(completion), "If deterministic is a list, it must have the same length as the number of tokens to be scored, but is {} and {}".format(deterministic, completion)
                deterministic_flags = np.concatenate([s.deterministic, np.array(deterministic[:1])], dtype=np.bool_)
                next_deterministic = np.array(deterministic[1:])

            return dc.detseq(ids=np.concatenate([s.input_ids, completion[:1]], axis=0), 
                    next_ids=completion[1:],
                    logprobs=np.concatenate([s.logprobs, token_score[:1]], axis=0),
                    next_logprobs=token_score[1:],
                    deterministic=deterministic_flags,
                    next_deterministic=next_deterministic,
                    predecessor=s,
                    user_data=user_data,
                    stop_phrase=np.concatenate([s.stop_phrase, np.array([stop_phrase])]),
                    needs_rewrite=needs_rewrite,
                    sticky_user_data_keys=s.sticky_user_data_keys,
                    internal=internal
            )
        results = []

        async for (s, tokens, scores) in self.score_tokens(sqs, tokens, max_batch_size=max_batch_size, noscore=noscore):
            results.append(make_detseq(s, scores, tokens))

        return results
    
    async def score_tokens(self, sqs: List[dc.DecoderSequence], tokens: List[List[int]], max_batch_size=None, noscore=False):
        completion = [np.array(cont) for cont in tokens]

        for s, tokens, scores in zip(sqs, completion, await asyncio.gather(*(self._score_next_tokens(s, compl, noscore=noscore) for s, compl in zip(sqs, completion)))):
            yield (s, tokens, scores)

class lmtp_model:
    """
    Factory class for LMTPDcModelCls client instances.

    In case of inprocess=True, lmtp_model keeps a reference to the internally instantiated 
    LMTPMultiProcessingClient to share it between all uses of the resulting LMTPDcModelCls 
    across several queries.
    """
    def __init__(self, model_identifier, inprocess=False, endpoint=None, async_transport=False, **kwargs):
        self.model_identifier = model_identifier
        self.tokenizer_identifier = kwargs.pop("tokenizer", self.model_identifier)

        self.inprocess = inprocess
        self.async_transport = async_transport
        self.endpoint = endpoint
        self.kwargs = kwargs

        self.lmtp_inprocess_client = None
    
    # ensures that all inprocess lmtp models instantiated via this class 
    # share the same underlying LMTPMultiProcessingClient instance
    # (uses reference counting to ensure that the client is only shut down 
    # once all LMTPDcModel instances have closed)
    def inprocess_client_constructor_factory(self, identifier, **kwargs):
        assert identifier == self.model_identifier, "Model identifier mismatch: {} vs {}".format(self.model_identifier, identifier)
        
        # use in-process, async client
        if self.async_transport:
            return LMTPAsyncClient(identifier, **kwargs)

        # otherwise, use multiprocessing
        from .lmtp_multiprocessing import LMTPMultiProcessingClient

        if self.lmtp_inprocess_client is None:
            # ref owned by self
            self.lmtp_inprocess_client = LMTPMultiProcessingClient(identifier, **kwargs).ref()
            # ref owned by caller
            return self.lmtp_inprocess_client.ref()
        
        # ref owned by caller
        return self.lmtp_inprocess_client.ref()

    def __del__(self):
        if self.lmtp_inprocess_client is not None:
            try:
                if asyncio.get_event_loop() == asyncio.get_event_loop_policy().get_event_loop():
                    pass
                else:
                    asyncio.ensure_future(self.lmtp_inprocess_client.close())
            except RuntimeError as e:
                # ignore if event loop has already been shut down
                if "no current event loop" in str(e): pass
                else: raise e

    def __call__(self) -> ModelAPIAdapter:
        # reference to factory instance
        this = self

        class LMTPAdapterModel(ModelAPIAdapter):
            def __init__(self) -> None:
                self.model_identifier = this.model_identifier
                self.served_model = None
                self._tokenizer = None

                self.decoder_args = {}

                self.num_queries = 0

            def __str__(self):
                return "<LMTPAdapterModel {}>".format(self.model_identifier)

            def get_tokenizer(self):
                if self._tokenizer is None:
                    self._tokenizer = tokenizer(this.tokenizer_identifier, **this.kwargs)
                self.served_model = self
                return self._tokenizer

            def get_dclib_model(self):
                inprocess_client_constructor = None

                if this.inprocess:
                    lmtp_server_kwargs = this.kwargs
                    inprocess_client_constructor = this.inprocess_client_constructor_factory
                else:
                    lmtp_server_kwargs = None

                full_args = {**this.kwargs, **self.decoder_args}
                for key in ["inprocess", "endpoint", "lmtp_server_kwargs", "inprocess_client_constructor", "model"]:
                    full_args.pop(key, None)

                return LMTPDcModel(self, self.get_tokenizer(), inprocess=this.inprocess, endpoint=this.endpoint, lmtp_server_kwargs=lmtp_server_kwargs, 
                                 inprocess_client_constructor=inprocess_client_constructor, **full_args)

            async def tokenize(self, text):
                return self.get_tokenizer().tokenize(text, asbytes=True)
            
            async def detokenize(self, input_ids):
                return self.get_tokenizer().decode(input_ids)

        return LMTPAdapterModel()
