"""
A client/server implementation for LMTP that runs the model 
asynchronously in the same process.
"""

import asyncio
import pickle

from .lmtp_scheduler import TokenSession, Scheduler
from .errors import LMTPStreamError

class LMTPAsyncTransport:
    def __init__(self, queue):
        self.queue: asyncio.Queue = queue

    async def send(self, type, payload):
        self.queue.put_nowait((type, payload))

def ensure_picklable(kwargs, msg=""):
    try:
        # make sure kwargs can be pickled
        pickle.dumps(kwargs)
    except Exception as e:
        raise AssertionError(msg)


async def lmtp_inference_task(model_identifier, token_queue: asyncio.Queue, cmd_queue: asyncio.Queue, kwargs):
    transport = LMTPAsyncTransport(token_queue)
    
    scheduler = Scheduler.instance(model_identifier, kwargs, user=transport, only_existing=False, sync=True)
    scheduler_task = scheduler.async_worker()
    session = TokenSession(transport, kwargs, static=True)

    async def session_task():
        while True:
            msg = await cmd_queue.get()
            if msg is None: continue
            type, payload = msg
            await session.handle(type, payload)
    
    await asyncio.gather(scheduler_task, session_task())

class LMTPAsyncClient:
    """
    Allows use of a LMTP TokenSession from within the same process (model calls are async).

    Note that this type of transport is only suitable for very fast, non-blocking model calls,
    as otherwise the asyncio event loop will be blocked during each model call, which adds 
    a lot of latency.
    """

    def __init__(self, model_identifier, **kwargs):
        self.model_identifier = model_identifier

        self.cmd_queue = asyncio.Queue()
        self.token_queue = asyncio.Queue()
        self.inference_task = asyncio.create_task(lmtp_inference_task(self.model_identifier, self.token_queue, self.cmd_queue, kwargs))
        
        self.stream_id = 0
        self.iterators = {}

        self.poll_task = asyncio.create_task(self.poll_messages())
        self.poll_running = asyncio.Event()

    def __del__(self):
        if self.poll_task is not None and self.poll_running.is_set():
            self.poll_task.cancel()

    async def poll_messages(self):
        try:
            self.poll_running.set()

            while True:
                if self.token_queue.empty():
                    await asyncio.sleep(0.001)
                    continue
                try:
                    msg = await self.token_queue.get()
                    if msg is None: continue
                    type, d = msg
                    
                    if type == "TOKEN":
                        stream_id = d["stream_id"]
                        consumers = self.iterators.get(stream_id, [])
                        for q in consumers: q.put_nowait(d)
                except Exception as e:
                    print("failed to handle msg", e, flush=True)
        except asyncio.CancelledError:
            return

    async def close(self):
        if self.poll_task is not None and self.poll_running.is_set():
            self.poll_task.cancel()
        for itr_list in self.iterators.values():
            for it in itr_list:
                it.put_nowait(None)

    async def generate(self, prompt, **kwargs):
        self.stream_id += 1
        payload = {
            **kwargs,
            "model": self.model_identifier,
            "prompt": prompt,
            "stream_id": self.stream_id
        }

        if payload.get("logit_bias", None) is None:
            payload.pop("logit_bias", None)

        self.cmd_queue.put_nowait(("GENERATE", payload))

        async for token in self.stream_iterator(self.stream_id):
            yield token

    async def score(self, prompt, scored_prompt, **kwargs):
        self.stream_id += 1
        payload = {
            **kwargs,
            "model": self.model_identifier,
            "prompt": prompt,
            "scored": scored_prompt,
            "stream_id": self.stream_id
        }

        self.cmd_queue.put_nowait(("SCORE", payload))

        async for token in self.stream_iterator(self.stream_id):
            yield token

    async def stream_iterator(self, stream_id):
        q = asyncio.Queue()
        self.iterators.setdefault(stream_id, []).append(q)
        
        while True:
            item = await q.get()

            if item is None: 
                break
            
            if item.get("error") is not None:
                raise LMTPStreamError(item["error"])

            if item.get("finish_reason") is not None:
                yield item
                break
            yield item