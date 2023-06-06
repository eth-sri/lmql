from lmql.runtime.dclib.dclib_model import DcModel
from lmql.runtime.tokenizer import load_tokenizer
from .lmtp_client import LMTPWebSocketClient
from .lmtp_multiprocessing import LMTPMultiProcessingClient
from .lmtp_threading import LMTPThreadedClient
from .lmtp_server import Scheduler
import lmql.runtime.dclib as dc
import asyncio
import numpy as np
import aiohttp
import lmql.utils.nputil as nputil
import lmql.runtime.masks as masks
from lmql.runtime.token_distribution import TokenDistribution

from typing import List, Union

class LMTPModel(DcModel):
    def __init__(self, model, tokenizer, endpoint, inprocess=False, truncation_threshold=-3e+38, init_workers=True, lmtp_server_kwargs=None, **kwargs):
        super().__init__(model, tokenizer, truncation_threshold, init_workers, **kwargs)

        self.model.chunk_size = kwargs.get("chunksize", 16)

        # LMTP client object (can be inprocess or websocket)
        self.client = None
        # asyncio task for client loop
        self._client_loop = None
        # set once self.client is set up
        self.connected_signal = asyncio.Event()
        # set to termiante self._client_loop
        self.close_signal = asyncio.Event()
        
        # endpoint in case of remote model
        self.endpoint = endpoint
        if endpoint is not None and not self.endpoint.startswith("http"):
            self.endpoint = "http://" + self.endpoint

        self.inprocess = inprocess
        self.lmtp_server_kwargs = lmtp_server_kwargs
        assert self.inprocess or  lmtp_server_kwargs is None, "LMTP server kwargs can only be set when using lmql.inprocess mode"

        # model statistics
        self.requests = 0
        self.tokens = 0

    async def inprocess_client_loop(self):
        self.client = LMTPMultiProcessingClient(self.model.model_identifier, **self.lmtp_server_kwargs)

        self.connected_signal.set()
        await self.close_signal.wait()
        await self.client.close()
        self.client = None

    async def ws_client_loop(self):
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(self.endpoint) as ws:
                self.client = LMTPWebSocketClient(self.model.model_identifier, ws)
                self.client.connect()
                
                self.connected_signal.set()
                await self.close_signal.wait()

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
        if self.client is None:
            if not self.inprocess:
                self._client_loop = asyncio.create_task(self.ws_client_loop())
            else:
                self._client_loop = asyncio.create_task(self.inprocess_client_loop())
        await self.connected_signal.wait()

    # on deinit
    def close(self):
        self.close_signal.set()

    def __del__(self):
        self.close_signal.set()

    def make_logits(self, payload):
        scores = {}
        for t, score in payload["top_logprobs"].items():
            scores[int(t)] = score
        scores[int(payload["token"])] = payload["logprob"]
        scores = scores.items()

        logits = np.ones(self.tokenizer.vocab_size) * self.truncation_threshold
        logits[[t for t, _ in scores]] = [s for _, s in scores]

        return logits

    async def singleton_result(self, token, score):
        yield {"token": token, "logprob": score, "top_logprobs": {token: score}}

    async def generate(self, s, temperature, top_logprobs = 1, chunk_size=None, **kwargs):
        if chunk_size is None:
            chunk_size = self.model.chunk_size
        kwargs = {**self.model_args, **kwargs}

        constrained_seqs = np.array([s.is_query_constrained], dtype=np.bool_)
        logits_mask_result = await self.compute_logits_mask(s.input_ids.reshape(1, -1), [s.user_data], constrained_seqs, [s], **kwargs)

        mask = logits_mask_result.logits_mask[0]

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

        ids = self.tokenizer.convert_bytes_to_ids(s.input_ids)

        return self.client.generate(ids, max_tokens=chunk_size, temperature=temperature, logit_bias=mask, top_logprobs=top_logprobs)

    async def argmax(self, sequences: dc.DataArray, **kwargs):
        return await self.sample(sequences, temperature=0.0, **kwargs)

    async def sample(self, sequences: dc.DataArray, temperature, **kwargs):
        await self.ensure_connected()
        
        sampling_mode = "top-1" if temperature == 0.0 else "sample-{}".format(temperature)

        assert kwargs.get("num_samples", 1) == 1, "LMTPModel does not support num_samples != 1"

        async def op_sample(seqs):
            if len(seqs) == 0:
                return []
            
            if all(type(s) is dc.DeterministicDecoderSequence for s in seqs) and all(len(s.next_ids) > 0 for s in seqs):
                next_token_ids = np.array([s.next_ids[0] for s in seqs])
                next_token_scores = np.array([s.next_logprobs[0] for s in seqs])
                next_token_ids = np.array([self.tokenizer.decode_bytes([t])[0] for t in next_token_ids])
                return [s.make_successors(next_token_ids[i].reshape(1), next_token_scores[i], logits=None) for i,s in enumerate(seqs)]
            
            self.model.num_queries += len(seqs)
            tokens = await asyncio.gather(*[self.stream_and_return_first(s, await self.generate(s, temperature=temperature, **kwargs), sampling_mode) for s in seqs])

            next_token_ids = np.array([t['token'] for t in tokens], dtype=np.int64)
            next_token_scores = np.array([t['logprob'] for t in tokens], dtype=np.float32)
            next_logits = np.array([self.make_logits(t) for t in tokens], dtype=np.float32)

            next_tokens = np.array([self.tokenizer.decode_bytes([t])[0] for t in next_token_ids])

            return [s.make_successors(next_tokens[i].reshape(1), next_token_scores[i], logits=next_logits[i]) for i,s in enumerate(seqs)]
        
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
        
        scores = []
        i = 0
        
        ids = self.tokenizer.convert_bytes_to_ids(s.input_ids)
        next_tokens = self.tokenizer.convert_bytes_to_ids(next_tokens)

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
                deterministic_flags = np.concatenate([s.deterministic, np.array([deterministic])])
                next_deterministic = np.array([deterministic] * len(completion[1:]))
            else:
                assert type(deterministic) is list and len(deterministic) == len(completion), "If deterministic is a list, it must have the same length as the number of tokens to be scored, but is {} and {}".format(deterministic, completion)
                deterministic_flags = np.concatenate([s.deterministic, np.array(deterministic[:1])])
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

def lmtp_model(model_identifier, inprocess=False, endpoint=None, **kwargs):
    class LMTPModelCls:
        def __init__(self) -> None:
            self.model_identifier = model_identifier
            self.served_model = None
            self._tokenizer = None

            self.decoder_args = {}

            self.num_queries = 0

        def get_tokenizer(self):
            if self._tokenizer is None:
                self._tokenizer = load_tokenizer(self.model_identifier)
            self.served_model = self
            return self._tokenizer

        def get_dclib_model(self):
            bos_token_id = self.get_tokenizer().bos_token_id
            eos_token_id = self.get_tokenizer().eos_token_id

            dc.set_dclib_tokenizer(self.get_tokenizer())

            if inprocess:
                lmtp_server_kwargs = kwargs
            else:
                lmtp_server_kwargs = None

            return LMTPModel(self, self.get_tokenizer(), inprocess=inprocess, endpoint=endpoint, lmtp_server_kwargs=lmtp_server_kwargs, **self.decoder_args)

        async def tokenize(self, text):
            return self.get_tokenizer().tokenize(text, asbytes=True)
        
        async def detokenize(self, input_ids):
            return self.get_tokenizer().decode(input_ids)

        def sync_tokenize(self, text):
            return self.get_tokenizer()(text)["input_ids"]
        
        def report_metrics(self, metrics):
            pass

    return LMTPModelCls
