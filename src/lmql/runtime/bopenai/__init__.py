from .batched_openai import AsyncOpenAIAPI, async_buffer, response_buffer
import openai as openai

# redirects to openai.*
organization = None
api_key = None

# mock OpenAI Completion API
global _api
_api = None

def get_stats():
    global _api
    if _api is None:
        _api = AsyncOpenAIAPI()
    return _api.stats

def reset_latency_stats():
    global _api
    if _api is None:
        _api = AsyncOpenAIAPI()
    _api.reset_latency_stats()

def get_first_token_latency():
    global _api
    if _api is None:
        _api = AsyncOpenAIAPI()
    return _api.first_token_latency
class AsyncConfiguration:
    @staticmethod
    def set_batch_size(bs):
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        _api.batch_size = bs

    @staticmethod
    def set_maximum_collection_period(mcp):
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        _api.maximum_collection_period = mcp

    @staticmethod
    def set_tokenizer(ts):
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        _api.tokenizer = ts

    def get_stats():
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        return _api.stats
class Completion:
    @staticmethod
    def set_chaos(prob):
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        _api.set_chaos(prob)
    
    @staticmethod
    def get_stats():
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        return _api.stats

    @staticmethod
    def start_stats_logger():
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        _api.start_stats_logger()

    @staticmethod
    def stop_stats_logger():
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        _api.stop_stats_logger()

    @staticmethod
    def set_use_stream(v):
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        _api.nostream = not v

    @staticmethod
    async def create(*args, **kwargs):
        global _api
        if _api is None:
            _api = AsyncOpenAIAPI()
        return await _api.complete(*args, **kwargs)