import openai
import traceback
import asyncio
import sys
from dataclasses import dataclass
import random
import pickle
import os
import time
from functools import total_ordering

from .openai_api import complete, OpenAIRateLimitError, Capacity

global logit_bias_logging
logit_bias_logging = True

def set_logit_bias_logging(value):
    global logit_bias_logging
    logit_bias_logging = value

class EmptyStreamError(Exception): pass
class ChaosException(openai.APIError): pass
class APIShutDownException(RuntimeError): pass
class MaximumRetriesExceeded(Exception): 
    def __init__(self, error: Exception, retries: int):
        self.error = error
        self.retries = retries
    
    def __str__(self):
        print(self.error)
        return f"Maximum retries exceeded ({self.retries}) with error {type(self.error)}: {str(self.error)}"

class Batcher:
    def __init__(self, batch_size: int):
        self.tasks = []
        self.queued_requests = []
        self.batch_size = batch_size
    
    async def fill(self, queue: asyncio.Queue, maximum_collection_period: float = 0.1):
        if len(self.tasks) >= self.batch_size:
            return
        # first item is blocking call
        i = (await queue.get()).kwargs
        self.tasks.append(i)
        self.fill_nowait(queue)
        if len(self.tasks) <= self.batch_size:
            # wait some time if batch is not full yet
            await asyncio.sleep(maximum_collection_period)
            self.fill_nowait(queue)
        self.group()

    def fill_nowait(self, queue: asyncio.Queue):
        if queue.empty():
            pass
        else:
            try:
                while True and len(self.tasks) < self.batch_size:
                    self.tasks.append(queue.get_nowait().kwargs)
            except asyncio.QueueEmpty:
                pass
        
    def task_type(self, task):
        keys = ["model", "max_tokens", "temperature", "logprobs", "user", "logit_bias", "echo"]
        def get(k): 
            if k == "logit_bias": return "-".join([f"{k}={v}" for k,v in sorted(task.get(k, {}).items())])
            return str(task.get(k, "<none>"))
        identifier = "|".join([f"{k}={get(k)}" for k in keys])
        # check for str or int prompt
        if isinstance(task["prompt"], str):
            identifier += "-str"
        else:
            identifier += "-int"
        
        return identifier

    def group(self):
        assert len(self.queued_requests) == 0, f"Batcher.groups() called before self.queued_requests was emptied"

        buckets = {}
        
        for t in self.tasks:
            identifier = self.task_type(t)
            buckets.setdefault(identifier, []).append(t)
        
        for bucket in buckets.values():
            if "turbo" in bucket[0]["model"]:
                for t in bucket:
                    self.queued_requests.append(make_request_args([t]))
                continue
            self.queued_requests.append(make_request_args(bucket))
        
        self.tasks = []

def make_request_args(tasks):
    prompts = [t["prompt"] for t in tasks]
    futures = [t["future"] for t in tasks]
    request_ids = [t["request_id"] for t in tasks]

    api_configs = [t.get("api_config", None) for t in tasks if t.get("api_config") is not None]
    api_config = api_configs[0] if len(api_configs) > 0 else None

    timeouts = [t.get("timeout", None) for t in tasks if t.get("timeout") is not None]
    timeout = max(timeouts) if len(timeouts) > 0 else None

    # construct request arguments
    request_args = tasks[0].copy()
    del request_args["future"]
    
    request_args["prompt"] = prompts
    request_args["futures"] = futures
    request_args["request_id"] = request_ids
    request_args["stream"] = True
    request_args["timeout"] = timeout
    
    if api_config is not None: 
        request_args["api_config"] = api_config

    return request_args

@dataclass
class Stats:
    prompt_tokens: int = 0
    tokens: int = 0
    requests: int = 0
    errors: int = 0
    sum_batch_size: int = 0

    def reset(self):
        self.tokens = 0
        self.requests = 0
        self.errors = 0
        self.sum_batch_size = 0

    def print(self):
        print(f"OpenAI API Stats: {self.requests} requests, {self.errors} errors, {self.tokens} tokens, {self.sum_batch_size} batch size, {float(self.sum_batch_size)/max(1,self.requests)} average batch size")
    
    def __str__(self):
        return f"OpenAI API Stats: {self.requests} requests, {self.errors} errors, {self.tokens} tokens, {float(self.sum_batch_size)/max(1,self.requests)} average batch size, reserved capacity {Capacity.reserved}/{Capacity.total}"

    def cost_estimate(self, model):
        k_tokens = float(self.tokens) / 1000

        # translate the above to python
        if model is None:
            print("warning: cost_estimate(): no model specified.")
            return -1
        if "text-davinci" in model:
            return k_tokens * 0.02
        elif "text-ada" in model:
            return k_tokens * 0.0004
        elif "text-babbage" in model:
            return k_tokens * 0.0005
        elif "text-curie" in model:
            return k_tokens * 0.002
        else:
            print("warning: cost_estimate(): unknown model {}".format(model))
            return -1

class ResponseStream:    
    def __init__(self, scheduler, kwargs, response, n, request_ids, maximum_retries=20, chaos = None, stats: Stats=None):
        self.scheduler: AsyncOpenAIAPI = scheduler
        self.kwargs = kwargs
        self.response = response
        self.request_ids = request_ids
        self.slices = [ResponseStreamSlice(self, self.view_kwargs(i), maximum_retries=maximum_retries) for i in range(n)]
        self.chaos = chaos
        self.stats = stats

        self.stats.requests += 1
        self.stats.sum_batch_size += n

        # task that always waits for new data in the response stream
        self.iteration_task = asyncio.create_task(self.iter_task())
    
    def view_kwargs(self, i):
        kwargs = self.kwargs.copy()
        kwargs["prompt"] = kwargs["prompt"][i]
        kwargs["request_id"] = self.request_ids[i]
        return kwargs

    def __del__(self):
        self.iteration_task.cancel()

    async def iter_task(self):
        try:
            self.response = aiter(self.response)
            async for data in self.response:
                if self.chaos is not None and random.random() > (1.0 - self.chaos):
                    raise ChaosException()
                
                if not "choices" in data.keys():
                    print("No choices in data", data)
                    continue

                for c in data["choices"]:
                    index = c["index"]

                    self.stats.tokens += len(c["logprobs"]["tokens"])
                    assert c is not None
                    self.slices[index].digest(c)
                    self.slices[index].finish_reason = c["finish_reason"]
                    
                    # logprobs.tokens, text, logprobs.token_logprobs
            for c in self.slices:
                c.finish()
        except Exception as e:
            print("Failed with", e)
            for c in self.slices:
                c.error(e)

    def view(self, index):
        assert index < len(self.slices), f"index {index} out of bounds for {len(self.slices)} slices of response stream"
        return self.slices[index]

@dataclass
class RecoveryAttempt:
    kwargs: dict
    error: Exception
    maximum_retries: int


class response_buffer_slice:
    def __init__(self, buffer, lower):
        self.buffer = buffer
        self.lower = lower
    
    def __str__(self) -> str:
        buffered_tokens = max(0, self.buffer.num_tokens - self.lower)
        return "<response_buffer_slice lower={} tokens_left≥{} >".format(self.lower, buffered_tokens)

    def __repr__(self) -> str:
        return str(self)

    async def empty(self):
        try:
            await self.get(0)
            return False
        except IndexError:
            return True

    async def get(self, i):
        return await self.buffer.get(i + self.lower)

    def __getitem__(self, i):
        if type(i) is slice:
            return response_buffer_slice(self.buffer, self.lower + i.start)
        assert False, f"response_buffer_slice.__getitem__({i}) not supported. Use async get() instead."

async def async_buffer(iterator, eager=False, tokenizer=None):
    if type(iterator) is list:
        # wrap already buffered data as response_buffer
        return response_buffer(None, iterator, tokenizer=tokenizer)

    if eager:
        data = []
        async for i in iterator: data.append(i)
        return response_buffer(None, data, tokenizer=tokenizer)
    else:
        if type(iterator) is ResponseStreamSlice:
            iterator = aiter(iterator)
        return response_buffer(iterator, tokenizer=tokenizer)
class response_buffer:
    def __init__(self, iterator, fixed_data=None, tokenizer=None):
        self.iterator = iterator

        self.text = ""
        self.num_tokens = 0
        self.logprobs = {
            "text_offset": [],
            "token_logprobs": [],
            "tokens": [],
            "top_logprobs": []
        }

        if fixed_data is not None:
            self.fixed = True
            self._append(fixed_data)
            self.tokenizer = None
        else:
            self.fixed = False
            # when provided, convert ["logprobs"]["tokens"] to token IDs automatically
            self.tokenizer = tokenizer
            assert self.tokenizer is not None, f"response_buffer: tokenizer must be provided when using non-fixed data"
            

    def __str__(self) -> str:
        return "<response_buffer num_tokens={} iterator={}>".format(self.num_tokens, self.iterator)
    
    @classmethod
    def singleton(cls, text=None, text_offset=None, token_logprob=None, token=None, top_logprobs=None):
        return cls(None, {
            "text": text or "",
            "logprobs": {
                "text_offset": [text_offset],
                "token_logprobs": [token_logprob],
                "tokens": [token],
                "top_logprobs": [top_logprobs]
            }
        })


    def _append(self, data):
        self.text += data["text"]
        self.logprobs["text_offset"] += data["logprobs"]["text_offset"]
        self.logprobs["token_logprobs"] += data["logprobs"]["token_logprobs"]
        self.logprobs["tokens"] += data["logprobs"]["tokens"]
        self.logprobs["top_logprobs"] += data["logprobs"]["top_logprobs"]
        
        self.num_tokens = len(self.logprobs["tokens"])

    # allow async iteration over response buffer
    def __aiter__(self):
        async def _aiter():
            i = 0
            while True:
                try:
                    yield await self.get(i)
                    i += 1
                except IndexError:
                    break
        return _aiter()

    async def get(self, i):
        while self.num_tokens <= i and self.iterator is not None:
            try:
                chunk = await anext(self.iterator)
                self._append(chunk)
            except StopAsyncIteration:
                break
        if i >= self.num_tokens:
            raise IndexError(f"index {i} out of bounds for response_buffer of length {self.num_tokens}. Iterator is {self.iterator}")

        text_start = self.logprobs["text_offset"][i]
        text_end = self.logprobs["text_offset"][i+1] if i+1 < len(self.logprobs["text_offset"]) else None
        
        return {
            "text": self.text[text_start:text_end],
            "logprobs": {
                "text_offset": self.logprobs["text_offset"][i],
                "token_logprobs": self.logprobs["token_logprobs"][i],
                "tokens": self.logprobs["tokens"][i],
                "top_logprobs": self.logprobs["top_logprobs"][i]
            },
            **({"fixed": True} if self.fixed else {})
        }
    
    async def empty(self):
        try:
            await self.get(0)
            return False
        except IndexError:
            return True

    def __getitem__(self, i):
        # slice 
        if isinstance(i, slice):
            assert i.stop is None, "slicing with stop index not supported on OpenAIResponseBuffer"
            assert i.step is None, "slicing with step not supported on OpenAIResponseBuffer"
            return response_buffer_slice(self, i.start)
        else:
            assert False, "only slicing supported on response_buffer. For single item access, use async get()"

class ResponseStreamSliceIterator:
    def __init__(self, slice):
        self.slice = slice
        self.retries = 0
        self.text = ""
        self.consumed_tokens = []
        self.n = 0

        self.waiting_tasks = []

    async def recover(self):
        recovery_kwargs = self.slice.kwargs.copy()
        # reconstruct the prompt by tokenizing the consumed tokens
        if len(self.consumed_tokens) > 0:
            prompt = self.consumed_tokens
            if type(prompt[0]) is str:
                recovery_kwargs["prompt"] = "".join([t for t in prompt])
            else:
                recovery_kwargs["prompt"] = [t[0] for t in prompt]
        
        # issue new completion call
        new_slice = await self.slice.stream.scheduler.complete(**recovery_kwargs)
        new_it = ResponseStreamSliceIterator(new_slice)
        new_it.retries = self.retries + 1

        # print("recovery for request with ID", recovery_kwargs["request_id"])
        
        # skip as many data packets as necessary to get to the original point of failure
        while len(new_it.consumed_tokens) < len(self.consumed_tokens):
            last_data = await anext(new_it)
            
            # if last chunk of new stream is too long, we return a partial chunk to align
            if len(new_it.consumed_tokens) > len(self.consumed_tokens):
                offset = len(new_it.consumed_tokens) - len(self.consumed_tokens)
                partial_data = {
                    "text": new_it.text[len(self.text):],
                    "logprobs": {
                        "text_offset": last_data["logprobs"]["text_offset"][-offset:],
                        "token_logprobs": last_data["logprobs"]["token_logprobs"][-offset:],
                        "tokens": last_data["logprobs"]["tokens"][-offset:],
                        "top_logprobs": last_data["logprobs"]["top_logprobs"][-offset:]
                    }
                }

                self.text = new_it.text
                self.consumed_tokens = new_it.consumed_tokens
                self.slice = new_slice
                self.retries = new_it.retries
                
                return partial_data
        self.text = new_it.text
        self.consumed_tokens = new_it.consumed_tokens
        self.slice = new_slice
        # otherwise the chunking aligns with the old stream, so we return the next chunk
        return await self.__anext__()
    
    def __del__(self):
        """Make sure to clean up any pending tasks."""
        for t in self.waiting_tasks:
            try:
                loop = asyncio.get_event_loop()
                if not t.done() and not loop.is_closed():
                    t.cancel()
            except RuntimeError:
                pass

    async def get_next(self):
        if self.slice.done.is_set(): 
            if self.n == 0:
                return RecoveryAttempt(self.slice.kwargs, TimeoutError(), self.slice.maximum_retries)
            raise StopAsyncIteration
        check_done_task = asyncio.create_task(self.slice.done.wait(), name="check_done_task")
        self.waiting_tasks.append(check_done_task)
        
        get_next_item_task = asyncio.create_task(self.slice.data_queue.get())
        done, pending = await asyncio.wait([get_next_item_task, check_done_task], 
            return_when=asyncio.FIRST_COMPLETED, timeout=self.slice.kwargs.get("timeout", 15.0))
    
        self.waiting_tasks.remove(check_done_task)

        if check_done_task in done:
            # this indicates the end of this response stream
            for t in pending: t.cancel()
            if self.n == 0:
                return RecoveryAttempt(self.slice.kwargs, TimeoutError(), self.slice.maximum_retries)
            raise StopAsyncIteration
        elif len(done) > 0:
            assert get_next_item_task in done, f"expected get_next_item_task to be done, but only {done} is done."
            # cancel self.done waiting task
            for t in pending: t.cancel()
            check_done_task.cancel()
            # return with new data chunk
            self.n += 1
            return get_next_item_task.result()
        else:
            for t in pending: t.cancel()
            check_done_task.cancel()
            # if after timeout this response has been fully consumed, we are done
            if self.slice.done.is_set() and self.n > 0:
                raise StopAsyncIteration
            # otherwise return a RecoveryAttempt for retrying this request
            return RecoveryAttempt(self.slice.kwargs, TimeoutError(), self.slice.maximum_retries)

    async def __anext__(self):
        try:
            data = await self.get_next()
            # None indicates end of stream
            if data is None:
                if self.slice.done.is_set():
                    raise StopAsyncIteration
                else:
                    if self.slice.finish_reason != "length":
                        # return eos token as last item, if stream did not finish due to length
                        data = {
                            "text": "<|endoftext|>",
                            "logprobs": {
                                "text_offset": [0],
                                "token_logprobs": [0.0],
                                "tokens": ["<|endoftext|>"],
                                "top_logprobs": [{"<|endoftext|>": 0.0}]
                            }
                        }
                        self.slice.done.set()
                    else:
                        self.slice.done.set()
                        raise StopAsyncIteration
            # exceptions that are queued are definitive (all retries failed)
            if isinstance(data, Exception): raise data
            # RecoveryAttempt indicates that the underlying stream errored out and we need to recover (still retries left)
            if isinstance(data, RecoveryAttempt):
                if not self.slice.stream.scheduler.is_available():
                    # fail quietly, if parent scheduler is no longer available (results of this query will be discarded anyway)
                    raise StopAsyncIteration()
                # if the stream of our self.slice errors out, we can recover by creating a new 
                # stream via a new call to openai.Completion.create
                attempt: RecoveryAttempt = data
                print("OpenAI API: Underlying stream of OpenAI complete() call failed with error", type(attempt.error), attempt.error, f"Retrying... (attempt: {self.retries})", flush=True)
                self.retries += 1
                # if we have exceeded the maximum number of retries, raise the error
                if self.retries > attempt.maximum_retries:
                    raise MaximumRetriesExceeded(attempt.error, retries=self.retries)
                if self.slice.stream.scheduler.tokenizer is None:
                    print("Cannot recover from stream error without a configured tokenizer", flush=True)
                    raise attempt.error
                return await self.recover()
            
            self.consumed_tokens += data["logprobs"]["tokens"]
            self.text += data["text"]

            return data
        except asyncio.CancelledError:
            raise StopAsyncIteration

class ResponseStreamSlice:
    def __init__(self, stream, kwargs, maximum_retries=3):
        self.stream: ResponseStream = stream
        self.kwargs = kwargs
        self.maximum_retries = maximum_retries

        self.data_queue = asyncio.Queue()
        self.failed = False
        self.done = asyncio.Event()
        self.finish_reason = None

        self.itr = None

    def digest(self, data):
        assert not self.failed, f"digest called on failed slice"
        self.data_queue.put_nowait(data)

    def finish(self):
        assert not self.failed, f"finish called on failed slice"
        self.data_queue.put_nowait(None)

    def error(self, error):
        assert not self.failed, f"error called on failed slice"
        self.failed = True
        self.data_queue.put_nowait(RecoveryAttempt(self.kwargs, error, self.maximum_retries))

    def __aiter__(self):
        return ResponseStreamSliceIterator(self)


@dataclass
@total_ordering
class RequestQueueItem:
    kwargs: dict
    priority: int

    # comparison
    def __lt__(self, other):
        return self.priority < other.priority
    
    def __eq__(self, other):
        return self.priority == other.priority

class AsyncOpenAIAPI:
    def __init__(self):
        self.maximum_retries = 20
        
        self.complete_api_call_queue = asyncio.PriorityQueue()
        self.complete_api_worker = asyncio.create_task(self.api_complete_worker(self.complete_api_call_queue))
        
        self.request_ctr = 0
        self.request_ctr_offset = 1000000000
        
        self.complete_request_queue = asyncio.Queue()
        self.complete_request_workers = [asyncio.create_task(self.complete_request_worker(self.complete_request_queue)) for i in range(5)]

        self.stats_logger = None 
        
        # chaos debugging (introduces random failures in the OpenAI API)
        self.chaos = None
        self.warned_about_chaos = False
        
        self.batch_size = 20
        self.maximum_collection_period = 0.05

        self.stats = Stats()
        self.nostream = False
        
        # INTERNAL OPTION only. In theory we can do caching but there are consequences
        # deterministic sampling, large cache size, cache loading startup time, etc.
        # also, when exposed to clients, this should be implemented on a per query level, not per batches
        self.use_cache = False

        self.tokenizer = None
        
        self.cache = {}
        self.cache_dir = "."
        self.futures = set()
        self.restore_cache()

        self.first_token_latency = 0

    def reset_latency_stats(self):
        self.first_token_latency = 0

    def restore_cache(self):
        if not self.use_cache:
            return
        cache_file = "openai.completions.cache"
        if os.path.exists(os.path.join(self.cache_dir, cache_file)):
            with open(os.path.join(self.cache_dir, cache_file), "rb") as f:
                self.cache = pickle.load(f)
    
    def save_cache(self):
        cache_file = "openai.completions.cache"
        with open(os.path.join(self.cache_dir, cache_file), "wb") as f:
            pickle.dump(self.cache, f)

    def start_stats_logger(self):
        self.stats_logger = asyncio.create_task(self.stats_logger_worker())
    def stop_stats_logger(self):
        self.stats_logger.cancel()

    async def stats_logger_worker(self):
        while True:
            await asyncio.sleep(1)
            print(self.stats, flush=True)

    def warn_chaos(self):
        if self.chaos is not None:
            if self.warned_about_chaos: return
            print("warning: AsyncOpenAIAPI.set_chaos() is set to a value different from None. This is only for testing purposes and should not be used in production (makes OpenAI complete streams fail randomly on purpose).")
            self.warned_about_chaos = True

    def set_chaos(self, chaos):
        self.chaos = chaos
        self.warn_chaos()

    def __del__(self):
        if self.stats_logger is not None:
            self.stats_logger.cancel()
        # cancel the score worker task
        self.complete_api_worker.cancel()
        for worker in self.complete_request_workers:
            worker.cancel()
        try:
            loop = asyncio.get_event_loop()
            while not all([t.done() for t in (self.complete_request_workers + [self.complete_api_worker])]):
                loop._run_once()
        except:
            pass # if no more event loop is around, no need to wait for the workers to finish

    async def api_complete_worker(self, queue):
        while True:
            self.futures = set([f for f in self.futures if not f.done()])
            while Capacity.reserved >= Capacity.total * 0.8:
                # print("wait before queing more requests", flush=True)
                await asyncio.sleep(0.1)
                # print(Capacity.reserved, Capacity.total, flush=True)
            # print(Capacity.reserved, Capacity.total, flush=True)
            batcher = Batcher(self.batch_size)
            await batcher.fill(queue, maximum_collection_period=self.maximum_collection_period)
            for kwargs in batcher.queued_requests:
                await self.complete_request_queue.put(kwargs)

    async def _create(self, **kwargs):
        async def first_buffered(aiter, first):
            yield first
            async for x in aiter:
                yield x

        num_prompt_tokens = sum([len(p) for p in kwargs["prompt"]])
        self.stats.prompt_tokens += num_prompt_tokens

        res = complete(**kwargs)
        first = await anext(res)
        return first_buffered(res, first)

    def is_definitive_error(self, e):
        if "logit biases, but can provide at most" in str(e):
            return True
        return False

    async def complete_request_worker(self, queue: asyncio.Queue):
        while True:
            try:
                kwargs = await queue.get()
                futures = kwargs.pop("futures")
                request_ids = kwargs.pop("request_id")
                retries = self.maximum_retries
                while True:
                    try:
                        if retries != self.maximum_retries:
                            print("Retrying", retries, "more times")
                            await asyncio.sleep(0.5)
                        task = asyncio.create_task(self._create(**kwargs))
                        res = await asyncio.wait_for(task, timeout=5.5)
                        break
                    except Exception as e:
                        if type(e) is AssertionError:
                            raise e
                        self.stats.errors += 1
                        retries -= 1            
                        print("OpenAI:", str(e), '"' + str(type(e)) + '"', flush=True)
                        # do not retry if the error is definitive (API configuration error)
                        if "api.env" in str(e): raise e
                        if kwargs.get("api_config", {}).get("errors", None) == "raise":
                            raise e
                        await asyncio.sleep(0.5)
                        if retries <= 0 or self.is_definitive_error(e):
                            raise e
                        if type(e) is TimeoutError or type(e) is OpenAIRateLimitError:
                            t = (2.0 * random.random()) ** (self.maximum_retries - retries)
                            print("Backing off for", t , "seconds")
                            await asyncio.sleep(t)
            except asyncio.CancelledError as e:
                break
            except Exception as e:
                print("error", type(e))
                for future in futures:
                    future.set_exception(e)
                continue

            self.warn_chaos() # warns about self.chaos if set

            rsi = ResponseStream(self, kwargs, res, len(futures), maximum_retries=self.maximum_retries, chaos=self.chaos, stats=self.stats, request_ids = request_ids)
            for i, future in enumerate(futures):
                future.set_result(rsi.view(i))

    async def complete(self, request_id=None, **kwargs):
        assert "prompt" in kwargs, f"bopenai requires prompt to be set"

        loop = asyncio.get_running_loop()
        result_fut = loop.create_future()
        self.futures.add(result_fut)

        if request_id is None:
            request_id = self.request_ctr
            self.request_ctr += 1
        else:
            print("re-trying request id", request_id)
        
        kwargs = {"future": result_fut, "request_id": request_id, **kwargs}
        
        if "logit_bias" in kwargs and len(kwargs["logit_bias"]) > 300:
            biases = list(kwargs["logit_bias"].items())
            # make sure to always include eos if set and truncating
            if 50256 in kwargs["logit_bias"]:
                biases = biases[:299] + [(50256, kwargs["logit_bias"][50256])]
            else:
                biases = biases[:300]
            global logit_bias_logging
            if logit_bias_logging:
                print("warning: the required logit_bias is too large to be handled by the OpenAI API and will be limited to the first 300 tokens. This can lead to the violation of the provided constraints or undesired model output. To avoid this use less broad or no constraints.", file=sys.stderr)
            kwargs["logit_bias"] = {t:b for t,b in biases}

        assert kwargs.get("echo", False), f"bopenai requires echo=True for to enable proper error recovery. Please handle proper prompt removal in client code."

        r = RequestQueueItem(kwargs, request_id)
        await self.complete_api_call_queue.put(r)
        self.request_ctr += 1
        if not self.is_available():
            raise APIShutDownException(f"bopenai requires at least one worker to be running to issue new complete requests.")
        return await result_fut

    def is_available(self):
        return len([w for w in self.complete_request_workers if not w.done()]) > 0