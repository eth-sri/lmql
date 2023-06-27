"""
A client/server implementation for LMTP that runs the model in a subprocess
and communicates with it via multiprocessing pipes (IPC).
"""

import multiprocessing
from multiprocessing.connection import Connection
import pickle
import sys
from .lmtp_client import *
from .lmtp_inference_server import TokenSession

async def multiprocessing_main_async(pipe: Connection, kwargs):
    transport = LMTPMultiprocessingTransport(pipe)
    session = TokenSession(transport, kwargs)

    try:
        while True:
            if not multiprocessing.parent_process().is_alive():
                print("[Parent process died, exiting]", flush=True)
                break

            if not pipe.poll():
                await asyncio.sleep(0.01)
                continue
                
            msg = pipe.recv()
            if msg is None: continue
            type, payload = msg
            await session.handle(type, payload)
    finally:
        sys.exit(0)


def multiprocessing_main(pipe: Connection, kwargs):
    asyncio.run(multiprocessing_main_async(pipe, kwargs))

class LMTPMultiprocessingTransport:
    def __init__(self, pipe):
        self.connection: Connection = pipe

    async def send(self, type, payload):
        self.connection.send((type, payload))

def ensure_picklable(kwargs, msg=""):
    try:
        # make sure kwargs can be pickled
        pickle.dumps(kwargs)
    except Exception as e:
        raise AssertionError(msg)

class LMTPMultiProcessingClientRef:
    def __init__(self, client):
        self.client = client
        self.refs = 0
    
    # forwarda ttribute access to generate, score
    def __getattr__(self, name):
        if name in ["generate", "score"]:
            return getattr(self.client, name)
        return super().__getattr__(name)

    async def close(self):
        assert self.refs > 0, "LMTPMultiProcessingClientRef.close() called too many times"
        
        self.refs -= 1
        if self.refs == 0:
            await self.client.close()

    def ref(self):
        self.refs += 1
        return self

class LMTPMultiProcessingClient:
    """
    Allows use of a LMTP TokenSession from within the same process (model runs in the same process too).
    """

    def __init__(self, model_identifier, **kwargs):
        ensure_picklable(kwargs, "lmtp.inprocess kwargs must be pickleable as it has to be sent to a subprocess")
        self.model_identifier = model_identifier

        (c2, c1) = multiprocessing.Pipe(duplex=True)
        self.subprocess = multiprocessing.Process(target=multiprocessing_main, args=(c1,kwargs), 
                                                  name="lmtp-model-server", daemon=True)
        self.subprocess.start()
        
        self.connection = c2
        
        self.stream_id = 0
        self.iterators = {}

        self.poll_task = asyncio.create_task(self.poll_messages())
        self.poll_running = asyncio.Event()

    def ref(self):
        return LMTPMultiProcessingClientRef(self).ref()

    def __del__(self):
        if self.poll_task is not None and self.poll_running.is_set():
            self.poll_task.cancel()

    async def poll_messages(self):
        try:
            self.poll_running.set()

            while True:
                if not self.connection.poll():
                    await asyncio.sleep(0.001)
                    continue
                try:
                    msg = self.connection.recv()
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
        self.subprocess.terminate()

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

        self.connection.send(("GENERATE", payload))

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

        self.connection.send(("SCORE", payload))

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