"""
Mocked aiohttp client session for use in pyodide.
"""

import asyncio
import js
from pyodide.ffi import to_js
import json

class EndStream: pass

class PostRequest:
    def __init__(self, url, headers, payload):
        self.url = url
        self.headers = headers
        self.payload = payload

        self.queue = asyncio.Queue()
        self.content = self

        async def data_handler(error, data):
            if error: 
                self.queue.put_nowait(EndStream)
            else: 
                self.queue.put_nowait(data.encode("utf-8"))

        self.completion_task = js.openai_completion_create(url, json.dumps(payload), data_handler)

    def close(self):
        self.completion_task.cancel()

    async def iter_any(self):
        while True:
            chunk = await self.queue.get()

            if chunk is EndStream:
                break
            else:
                yield chunk

    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass

class ClientSession:
    def post(self, url, headers, json):
        return PostRequest(url, headers, json)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass
