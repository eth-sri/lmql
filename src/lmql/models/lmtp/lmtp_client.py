"""
This file includes a simple 'websocket' based client for LMTP. 

For debugging purposes, run this file directly for an interactive client CLI.
"""

import aiohttp
import asyncio
import json
import sys
import warnings
from .errors import LMTPStreamError

class LMTPWebSocketClient:
    """
    Simple 'websockets' based client for LMTP.
    """
    def __init__(self, model_identifier, ws: aiohttp.ClientWebSocketResponse):
        self.ws = ws
        self.stream_id = 0
        self.model_identifier = model_identifier

        # for streamed responses
        self.iterators = {}
        # for non-streamed responses
        self.request_futures = {}

    async def request(self, name, payload):
        """
        Requests metadata about the configuration 
        of the currently running model.
        """
        self.stream_id += 1
        payload = {
            "stream_id": self.stream_id,
            "model": self.model_identifier,
            "data": payload
        }
        await self.ws.send_str("{} {}".format(name, json.dumps(payload)))

        # wait for response
        fut = asyncio.Future()
        self.request_futures[self.stream_id] = fut
        try:
            result = await asyncio.wait_for(fut, timeout=5)
        except TimeoutError as e:
            raise TimeoutError("LMTP request '{}' timed out after 5 seconds".format(name))

        self._model_info = result
        return result

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
        await self.ws.send_str("GENERATE {}".format(json.dumps(payload)))

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

        await self.ws.send_str("SCORE {}".format(json.dumps(payload)))

        async for token in self.stream_iterator(self.stream_id):
            yield token

    async def stream_iterator(self, stream_id):
        q = asyncio.Queue()
        self.iterators.setdefault(stream_id, []).append(q)
        
        while True:
            item = await q.get()

            if item.get("error") is not None:
                raise LMTPStreamError(item["error"])

            if item is None: 
                break
            if item.get("finish_reason") is not None:
                yield item
                break
            yield item

    def connect(self):
        async def msg_handler():
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        self.handle(msg)
                    except Exception as e:
                        warnings.warn("failed to handle msg {}: {}".format(msg, e))
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break
        self.handler = asyncio.create_task(msg_handler())

    def handle(self, msg):
        cmd, args = msg.data.split(" ",1)
        if cmd == "TOKEN":
            data = json.loads(args)

            for d in data:
                stream_id = d["stream_id"]
                consumers = self.iterators.get(stream_id, [])
                for q in consumers: q.put_nowait(d)
        elif cmd == "MSG":
            data = json.loads(args)
            
            for d in data:
                stream_id = d["stream_id"]

                fut = self.request_futures.pop(stream_id, None)
                if fut is not None:
                    fut.set_result(d)
        else:
            warnings.warn("Unknown command: {}".format(cmd))

def parse_kwargs(line):
    kwargs = {}
    prompt = ""
    for arg in line.split(" "):
        if "=" in arg:
            k, v = arg.split("=", 1)
            kwargs[k] = eval(v)
        elif len(kwargs) == 0:
            prompt += arg + " "
    return prompt, kwargs

async def interactive_client():
    import aioconsole
    import termcolor

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('http://workstation:8888') as ws:
            from lmql.runtime.tokenizer import tokenizer

            model = sys.argv[1]
            tokenizer = tokenizer(model)

            client = LMTPWebSocketClient(model, ws)
            client.connect()

            consumer_tasks = []

            while True:
                prompt = await aioconsole.ainput(">>>> ")
                prompt, kwargs = parse_kwargs(prompt)
                if prompt == "quit":
                    break
                prompt = tokenizer(prompt)["input_ids"]
                ids = [*prompt]

                async def consume():
                    try:
                        tokens = [*ids]
                        async for t in client.generate(ids, **kwargs):
                            tokens += [t["token"]]
                            print(t, flush=True)
                            termcolor.cprint(tokenizer.decode(tokens), flush=True, color="green")
                            print(">>>> ", end="", flush=True)
                    except Exception as e:
                        print("Failed to consume", e, flush=True)

                consumer_tasks.append(asyncio.create_task(consume()))
            
            print("[LMTP connection closed]", flush=True)

# time.sleep(1.5)
# print("Starting LMTP client", flush=True)
if __name__ == "__main__":
    asyncio.run(interactive_client())