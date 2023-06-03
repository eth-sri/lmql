import aiohttp
from aiohttp import web
import asyncio
import json
from dataclasses import dataclass
from queue import Queue, Empty as QueueEmpty
import threading
import time
import torch
import atexit

from transformers import AutoModelForCausalLM

@dataclass
class GenerateCall:
    prompt: str
    logit_bias: dict
    kwargs: dict
    stream_id: int
    result_queue: Queue

    def put(self, token):
        self.result_queue.put(token)

    def generation_mode(self):
        # string that describes the generation mode for this call (same string = can run in batch)
        return f"{self.kwargs.get('temperature', 0.0)}"

@dataclass
class GenerateBatch:
    input_ids: list
    attention_mask: list
    
    temperature: float
    max_tokens: int
    logit_biases: list

    calls: list
    
    @classmethod
    def from_calls(cls, calls):
        input_ids = [c.prompt for c in calls]
        max_len = max(len(ids) for ids in input_ids)
        input_ids = [[0] * (max_len - len(ids)) + ids for ids in input_ids]
        attention_mask = [[0] * (max_len - len(ids)) + [1] * len(ids) for ids in input_ids]
        
        temperature = calls[0].kwargs.get("temperature", 0.0)
        max_tokens = max(c.kwargs.get("max_tokens", 32) for c in calls)
        logit_biases = [c.logit_bias or {} for c in calls]
        return cls(input_ids, attention_mask, temperature, max_tokens, logit_biases, calls)

    def logits_processor(self):
        bias_tensors = None
        logit_biases = self.logit_biases

        class BatchLogitsProcessor:
            def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
                nonlocal bias_tensors

                vocab_size = scores.shape[-1]
                if bias_tensors is None:
                    bias_tensors = [torch.zeros(vocab_size) for _ in logit_biases]
                    for i, bias in enumerate(logit_biases):
                        if len(bias) > 0:
                            indices = torch.tensor(list(bias.keys()), dtype=torch.long)
                            values = torch.tensor(list(bias.values()), dtype=torch.float32)
                            bias_tensors[i][indices] = values
                    bias_tensors = torch.stack(bias_tensors).to(scores.device)
                
                return scores + bias_tensors

        return BatchLogitsProcessor()

    def generate_args(self):
        return {
            "input_ids": torch.tensor(self.input_ids),
            "do_sample": self.temperature > 0.0,
            "attention_mask": torch.tensor(self.attention_mask),
            "temperature": self.temperature,
            "max_new_tokens": self.max_tokens,
            "logits_processor": [self.logits_processor()],
            "output_scores": True,
            "return_dict_in_generate": True
        }

class TokenStreamer:
    def __init__(self, batch: GenerateBatch, eos_token_id, top_logprobs=1):
        self.batch = batch
        self.top_logprobs = top_logprobs
        self.eos_token_id = eos_token_id

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        self.log_token(input_ids, scores, **kwargs)
        return False

    def log_token(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, last=False, **kwargs):
        batch_size = input_ids.shape[0]
        
        last_tokens = input_ids[:, -1]
        last_scores = scores[-1]
        
        # for each sample get top logprobs
        top_logprobs = torch.topk(last_scores, self.top_logprobs, dim=-1, largest=True, sorted=True)
        for i in range(batch_size):
            logprobs = top_logprobs.values[i]
            tokens = top_logprobs.indices[i]

            token_payload = {
                "token": int(last_tokens[i].item()),
                "stream_id": self.batch.calls[i].stream_id,
                "logprob": float(logprobs[0].item()),
                "finish_reason": ("stop" if last_tokens[i].item() == self.eos_token_id else "length" if last else None),
                "top_logprobs": {
                    int(token.item()): float(logprob.item()) for logprob, token in zip(logprobs, tokens)
                }
            }

            self.batch.calls[i].put(token_payload)

class Scheduler:
    """
    A scheduler that takes calls to generate and batches them together. 

    Can be shared between multiple clients, make sure to call unregister(<user>) when done,
    to allow the scheduler to shut down when no longer needed by anyone.
    """
    def __init__(self, model_identifier):
        self.model_identifier = model_identifier
        self.queue = Queue()
        self.kill_event = threading.Event()
        
        self.worker_thread = threading.Thread(target=self.worker, daemon=True)
        self.worker_thread.start()

        self.users = set()
        self.last_use = time.time()

    def put(self, call: GenerateCall):
        self.queue.put(call)

    def batches(self):
        start = time.time()
        calls = []
        # get as many calls from the queue as possible within 0.1 seconds
        while time.time() - start < 0.1:
            try:
                calls.append(self.queue.get_nowait())
            except QueueEmpty:
                break
        # group calls into batches
        batches_by_mode = {}
        for c in calls:
            mode = c.generation_mode()
            batches_by_mode.setdefault(mode, []).append(c)
        return batches_by_mode.values()

    def worker(self):
        print("[Loading ", self.model_identifier, "]", flush=True, sep="")
        model = AutoModelForCausalLM.from_pretrained(self.model_identifier, device_map="auto")
        print("Ready", flush=True)

        while True:
            if self.kill_event.is_set():
                break

            for batch in self.batches():
                eos_token = model.config.eos_token_id

                try:
                    b = GenerateBatch.from_calls(batch)
                    streamer = TokenStreamer(b, model.config.eos_token_id)
                    kwargs = b.generate_args()
                    kwargs["input_ids"] = kwargs["input_ids"].to(model.device)
                    result = model.generate(**kwargs, stopping_criteria=[streamer], eos_token_id=eos_token, pad_token_id=eos_token)
                    streamer.log_token(result.sequences, result.scores, last=True)
                except Exception as e:
                    print("[Error during generate()]", e, flush=True)
                    for c in batch:
                        c.put({"error": str(e)})

    @staticmethod
    def instance(model_identifier, user):
        if model_identifier not in Scheduler._instances:
            Scheduler._instances[model_identifier] = Scheduler(model_identifier)

        s = Scheduler._instances[model_identifier]
        s.last_use = time.time()
        s.users.add(user)

        Scheduler.gc() # unload any unused models
    
        return s
    
    def unregister(self, user):
        self.users.remove(user)
        self.last_use = time.time()

    def dealloc(self):
        print("[Unloading ", self.model_identifier, "]", flush=True, sep="")
        Scheduler._instances.pop(self.model_identifier)
        
        self.kill_event.set()
        self.worker_thread.join()

    @staticmethod
    def gc(n: int = 2, timeout: int = 10):
        total = len(Scheduler._instances)
        not_needed = [k for k, v in Scheduler._instances.items() if len(v.users) == 0]

        if total >= n:
            for k in not_needed:
                s = Scheduler._instances[k]
                Scheduler._instances[k].dealloc()
        
        # total = len(Scheduler._instances)
        
        # if total >= n:
        #     print("[Warning] {} models loaded, even though the configured limit is {}. Not needed {}".format(total, n, len(not_needed)), flush=True)

Scheduler._instances = {}

class TokenSession:
    """
    A LMTP token session, which is a single user generating tokens with a fixed model, 
    using several token streams in parallel and varying sampling configurations.
    """
    def __init__(self, transport):
        self.transport = transport
        self.token_queue = Queue()
        self.queue_processor = asyncio.create_task(self.queue_loop())
        self.used_models = set()

    async def handle(self, cmd, kwargs):
        try:
            if not cmd == "GENERATE":
                raise Exception("Unknown command: {}".format(cmd))
            
            prompt = kwargs.pop("prompt")
            stream_id = kwargs.pop("stream_id")
            logit_bias = kwargs.pop("logit_bias", {})
            model = kwargs.pop("model")
            self.used_models.add(model)

            scheduler = Scheduler.instance(model, user=self)
            scheduler.put(GenerateCall(prompt, logit_bias, kwargs, stream_id, self.token_queue))
        except Exception as e:
            print(e, flush=True)

    async def queue_loop(self):
        try:
            while True:
                try:
                    token = self.token_queue.get_nowait()
                    await self.transport.send("TOKEN", token)
                except QueueEmpty:
                    await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            self.close()
        except Exception as e:
            print("TokenSession.queue_loop error", e, flush=True)
            self.close()

    def close(self):
        self.queue_processor.cancel()
        
        for m in self.used_models:
            if not m in Scheduler._instances:
                continue
            scheduler = Scheduler.instance(m, user=self)
            scheduler.unregister(self)
            Scheduler.gc(0)

class LMTPWebSocketTransport:
    """
    Exposes a LMTP TokenSession over a websocket.
    """
    def __init__(self, ws):
        self.ws = ws
        self.queue = asyncio.Queue()
        self._dumper = asyncio.create_task(self.dumper())

    async def dumper(self):
        while True:
            try:
                batch = [await self.queue.get()]
                # while len(batch) < 1:
                #     try:
                #         batch.append(await asyncio.wait_for(self.queue.get(), timeout=0.1))
                #     except asyncio.TimeoutError:
                #         break
                if len(batch) > 0:
                    await self.ws.send_str("TOKEN" + " " + json.dumps(batch))
            except asyncio.CancelledError:
                break
            except Exception as e:
                print("LMTPWebSocketTransport.dumper error", e, flush=True)

    async def send(self, type, payload):
        await self.queue.put(payload)

    @staticmethod
    async def listen(ws):
        transport = LMTPWebSocketTransport(ws)
        session = TokenSession(transport)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                cmd, kwargs = msg.data.split(" ", 1)
                
                kwargs = json.loads(kwargs)
                logit_bias = kwargs.pop("logit_bias", {})
                logit_bias = {int(k): float(v) for k, v in logit_bias.items()}
                kwargs["logit_bias"] = logit_bias
                
                await session.handle(cmd, kwargs)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break

        transport._dumper.cancel()
        session.close()
        await ws.close()

    async def close(self):
        await self.ws.close()

async def stream(request):
    # bidirectional websocket 
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await LMTPWebSocketTransport.listen(ws)

def main():
    app = web.Application()
    app.add_routes([web.get('/', stream)])
    web.run_app(app, host='localhost', port=8080)

if __name__ == "__main__":
    main()