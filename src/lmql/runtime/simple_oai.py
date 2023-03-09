import os

if "LMQL_BROWSER" in os.environ:
    import lmql.runtime.maiohttp as aiohttp
else:
    import aiohttp


import json
import time
import asyncio

# from openai_secret import openai_secret, openai_org

class OpenAIStreamError(Exception): pass
class OpenAIRateLimitError(OpenAIStreamError): pass

class Capacity: pass
Capacity.total = 32000 # defines the total capacity available to allocate to different token streams that run in parallel
# a value of 80000 averages around 130k tok/min on davinci with beam_var (lower values will decrease the rate and avoid rate limiting)
Capacity.reserved = 0

stream_semaphore = None

class CapacitySemaphore:
    def __init__(self, capacity):
        self.capacity = capacity

    async def __aenter__(self):
        # wait for self.capacity > capacity
        while True:
            if Capacity.reserved >= Capacity.total:
                await asyncio.sleep(0.5)
            else:
                Capacity.reserved += self.capacity
                break

    async def __aexit__(self, *args):
        Capacity.reserved -= self.capacity

class concurrent:
    def __init__(self, task):
        self.task = task

    def __enter__(self):
        self.task = asyncio.create_task(self.task)
        return self
    
    def __exit__(self, *args):
        self.task.cancel()

async def complete(**kwargs):
    global stream_semaphore

    num_prompts = len(kwargs["prompt"])
    max_tokens = kwargs.get("max_tokens", 0)

    async with CapacitySemaphore(num_prompts * max_tokens):
        from lmql.runtime.openai_secret import openai_secret, openai_org
        
        current_chunk = ""
        stream_start = time.time()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/completions",
                headers={
                    "Authorization": f"Bearer {openai_secret}",
                    "Content-Type": "application/json",
                },
                json={**kwargs},
            ) as resp:
                last_chunk_time = time.time()
                sum_chunk_times = 0
                n_chunks = 0
                current_chunk_time = 0

                async def chunk_timer():
                    nonlocal last_chunk_time, sum_chunk_times, n_chunks, current_chunk_time
                    while True:
                        await asyncio.sleep(0.5)
                        current_chunk_time = time.time() - last_chunk_time
                        # print("Average chunk time:", sum_chunk_times / n_chunks, "Current chunk time:", current_chunk_time)
                        # print("available capacity", Capacity.total - Capacity.reserved, "reserved capacity", Capacity.reserved, "total capacity", Capacity.total, flush=True)

                        if current_chunk_time > 1.5:
                            print("Token stream took too long to produce next chunk, re-issuing completion request. Average chunk time:", sum_chunk_times / max(1,n_chunks), "Current chunk time:", current_chunk_time, flush=True)
                            resp.close()
                            raise OpenAIStreamError("Token stream took too long to produce next chunk.")

                with concurrent(chunk_timer()):
                    async for chunk in resp.content.iter_any():
                        chunk = chunk.decode("utf-8")
                        current_chunk += chunk
                        is_done = current_chunk.strip().endswith("[DONE]")
                        
                        while "data: " in current_chunk:
                            chunks = current_chunk.split("data: ")
                            while len(chunks[0]) == 0:
                                chunks = chunks[1:]
                            if len(chunks) == 1:
                                # last chunk may be incomplete
                                break
                            complete_chunk = chunks[0].strip()
                            current_chunk = "data: ".join(chunks[1:])

                            if len(complete_chunk.strip()) == 0: 
                                continue
                            if complete_chunk == "[DONE]": 
                                return
                            
                            n_chunks += 1
                            sum_chunk_times += time.time() - last_chunk_time
                            last_chunk_time = time.time()
                            
                            data = json.loads(complete_chunk)

                            if "error" in data.keys():
                                message = data["error"]["message"]
                                if "rate limit" in message.lower():
                                    raise OpenAIRateLimitError(message + "local client capacity" + str(Capacity.reserved))
                                else:
                                    raise OpenAIStreamError(message + " (after receiving " + str(n_chunks) + " chunks. Current chunk time: " + str(time.time() - last_chunk_time) + " Average chunk time: " + str(sum_chunk_times / max(1, n_chunks)) + ")", "Stream duration:", time.time() - stream_start)

                            yield data
                        
                        if is_done: break
                    
                resp.close()

                if current_chunk.strip() == "[DONE]":
                    return
                
                try:
                    last_message = json.loads(current_chunk.strip())
                    message = last_message.get("error", {}).get("message", "")
                    if "rate limit" in message.lower():
                        raise OpenAIRateLimitError(message + "local client capacity" + str(Capacity.reserved))
                    else:
                        raise OpenAIStreamError(last_message["error"]["message"] + " (after receiving " + str(n_chunks) + " chunks. Current chunk time: " + str(time.time() - last_chunk_time) + " Average chunk time: " + str(sum_chunk_times / max(1, n_chunks)) + ")", "Stream duration:", time.time() - stream_start)
                        # raise OpenAIStreamError(last_message["error"]["message"])
                except json.decoder.JSONDecodeError:
                    raise OpenAIStreamError("Token stream ended unexpectedly.", current_chunk)

async def main():
    kwargs = {
        "model": "text-davinci-003",
        "prompt": "Say this is a test",
        "max_tokens": 7,
        "temperature": 0,
        "stream": True
    }

    async for chunk in complete(**kwargs):
        print(chunk)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())