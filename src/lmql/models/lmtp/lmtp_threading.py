"""
Thread-based LMTP client/server implementation.

Experimental and not usable with LMQL, due to threading issues.
"""

from queue import Queue
from .lmtp_client import *
import threading

async def threading_main_async(queue: Queue, token_queue: Queue, kill_event: threading.Event):
    transport = LMTPThreadingTransport(token_queue)
    session = TokenSession(transport)

    while True:
        if queue.qsize() == 0:
            await asyncio.sleep(0.01)
            continue
        
        if kill_event.is_set():
            session.close()
            print("[Parent process died, exiting]", flush=True)
            sys.exit(0)
        
        msg = queue.get()
        if msg is None: continue
        type, payload = msg
        await session.handle(type, payload)


def threading_main(queue: Queue, token_queue: Queue, kill_event: threading.Event):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(threading_main_async(queue, token_queue, kill_event))

class LMTPThreadingTransport:
    def __init__(self, queue):
        self.queue: Queue = queue

    async def send(self, type, payload):
        self.queue.put((type, payload))

class LMTPThreadedClient:
    """
    Allows use of a LMTP TokenSession where the server is running in a separate thread.

    Note: Currently this implementation has threading issues with LMQL and should not be used.
    """

    def __init__(self, model_identifier):
        self.model_identifier = model_identifier
        
        self.cmd_queue = Queue()
        self.token_queue = Queue()
        self.kill_event = threading.Event()

        self.server_thread = threading.Thread(target=threading_main, args=(self.cmd_queue, self.token_queue, self.kill_event), daemon=True)
        self.server_thread.start()
        
        self.stream_id = 0
        self.iterators = {}

        self.poll_task = asyncio.create_task(self.poll_messages())

    async def poll_messages(self):
        while True:
            if self.token_queue.qsize() == 0:
                await asyncio.sleep(0.001)
                continue
            try:
                msg = self.token_queue.get()
                if msg is None: continue
                type, d = msg
                
                if type == "TOKEN":
                    stream_id = d["stream_id"]
                    consumers = self.iterators.get(stream_id, [])
                    for q in consumers: q.put_nowait(d)
            except Exception as e:
                print("failed to handle msg", e, flush=True)

    async def close(self):
        for itr_list in self.iterators.values():
            for it in itr_list:
                it.put_nowait(None)
        self.kill_event.set()

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

        self.cmd_queue.put(("GENERATE", payload))

        async for token in self.stream_iterator(self.stream_id):
            yield token

    async def stream_iterator(self, stream_id):
        q = asyncio.Queue()
        self.iterators.setdefault(stream_id, []).append(q)
        
        while True:
            item = await q.get()

            if item is None: 
                break
            if item.get("finish_reason") is not None:
                yield item
                break
            yield item