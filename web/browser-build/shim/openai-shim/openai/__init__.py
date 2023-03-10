import js
from pyodide.ffi import to_js
import asyncio

organization = None
api_key = None

def autodict(o):
    if type(o) is dict:
        return AutoDictObject(o)
    elif type(o) is list:
        return [autodict(i) for i in o]
    else:
        return o

class AutoDictObject:
    def __init__(self, d):
        self.__dict__ = {k: autodict(v) for k, v in d.items()}

class Completion:
    @staticmethod
    async def create(model, prompt, max_tokens, temperature, logprobs, user, stream, logit_bias=None, **kwargs):
        all_data = []

        def on_data(error, data):
            if not error:
                all_data.append(autodict(data.to_py()))
            else:
                print("error", data)

        # example: ("text-ada-001", [[50256, 15496, 220]], 32, 0, 1, "lmql", true, (res) => {...})

        await js.openai_completion_create(
            model, to_js(prompt), max_tokens, temperature, logprobs, user, stream, to_js(logit_bias), on_data)

        return iter(all_data)


class APIError: pass