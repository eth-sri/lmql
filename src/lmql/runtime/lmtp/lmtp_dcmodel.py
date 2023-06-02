from lmql.runtime.dclib.dclib_model import DcModel
from lmql.runtime.tokenizer import load_tokenizer
from .lmtp_client import LMTPWebSocketClient
import lmql.runtime.dclib as dc
import asyncio
import numpy as np
import aiohttp

class LMTPModel(DcModel):
    def __init__(self, model, tokenizer, endpoint, truncation_threshold=-3e+38, init_workers=True, **kwargs):
        super().__init__(model, tokenizer, truncation_threshold, init_workers, **kwargs)

        self.close_signal = asyncio.Event()
        
        self.model.chunk_size = kwargs.get("chunksize", 16)

        self.client = None
        self._client_loop = asyncio.create_task(self.client_loop())
        self._connected_signal = asyncio.Event()
        
        self.endpoint = endpoint
        if not self.endpoint.startswith("http"):
            self.endpoint = "http://" + self.endpoint

        self.requests = 0
        self.tokens = 0

    async def client_loop(self):
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(self.endpoint) as ws:
                self.client = LMTPWebSocketClient(self.model.model_identifier, ws)
                self.client.connect()
                
                self._connected_signal.set()
                await self.close_signal.wait()

    def make_cache_entry(self, s, payload):
        scores = {}
        for t, score in payload["top_logprobs"].items():
            scores[int(t)] = score
        scores[int(payload["token"])] = payload["logprob"]

        top_entries = list(sorted(scores.items(), key=lambda x: x[1], reverse=True))
        tokens = [t for t, _ in top_entries]
        scores = [s for _, s in top_entries]
        edge_type = ["top-{}".format(i+1) for i in range(len(top_entries))]
        
        return (s, tokens, scores, edge_type, {})

    async def stream_and_return_first(self, s, iterator):
        item = await anext(iterator)
        self.requests += 1
        async def token_stream():
            self.tokens += 1
            yield self.make_cache_entry(s, item)

            async for payload in iterator:
                yield self.make_cache_entry(s, payload)
                self.tokens += 1
        self.register_token_stream(token_stream)
        
        return item

    async def ensure_connected(self):
        if self.client is None:
            self._client_loop = asyncio.create_task(self.client_loop())
        await self._connected_signal.wait()

    # on deinit
    async def close(self):
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

    async def argmax(self, sequences: dc.DataArray, **kwargs):
        await self.ensure_connected()

        async def op_argmax(seqs):
            if len(seqs) == 0:
                return []
            
            if all(type(s) is dc.DeterministicDecoderSequence for s in seqs) and all(len(s.next_ids) > 0 for s in seqs):
                next_token_ids = np.array([s.next_ids[0] for s in seqs])
                next_token_scores = np.array([s.next_logprobs[0] for s in seqs])
                return [s.make_successors(next_token_ids[i].reshape(1), next_token_scores[i], logits=None) for i,s in enumerate(seqs)]
            
            self.model.num_queries += len(seqs)
            tokens = await asyncio.gather(*[self.stream_and_return_first(s, self.client.generate(s.input_ids.tolist(), max_tokens=self.model.chunk_size, temperature=0.0)) for s in seqs])

            next_token_ids = np.array([t['token'] for t in tokens], dtype=np.int64)
            next_token_scores = np.array([t['logprob'] for t in tokens], dtype=np.float32)
            next_logits = np.array([self.make_logits(t) for t in tokens], dtype=np.float32)

            return [s.make_successors(next_token_ids[i].reshape(1), next_token_scores[i], logits=next_logits[i]) for i,s in enumerate(seqs)]
        
        return await sequences.aelement_wise(op_argmax)

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

def lmtp_model(model_identifier, endpoint=None):
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

            dc.set_dclib_tokenizer(dc.tokenizer("lmql-adapter-tokenizer", self.tokenize, self.detokenize, bos_token_id, eos_token_id))

            return LMTPModel(self, self.get_tokenizer(), endpoint=endpoint, **self.decoder_args)

        async def tokenize(self, text):
            return self.get_tokenizer()(text)["input_ids"]
        
        async def detokenize(self, input_ids):
            return self.get_tokenizer().decode(input_ids)

        def sync_tokenize(self, text):
            return self.get_tokenizer()(text)["input_ids"]
        
        def report_metrics(self, metrics):
            pass

    return LMTPModelCls
        