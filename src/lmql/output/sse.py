import lmql

from lmql.runtime.output_writer import BaseOutputWriter
from lmql import LMQLQueryFunction
import json

try:
    import aiohttp
    from aiohttp import web
    from aiohttp_sse import sse_response
except ImportError:
    raise ImportError("To use LMQL's server-sent events (SSE) output, you must install aiohttp and aiohttp_sse. Try: pip install aiohttp aiohttp_sse")

class EventStreamOutputWriter(BaseOutputWriter):
    def __init__(self, response):
        super().__init__(allows_input=False)
        self.response = response
    
    async def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables):
        chunk = f"{json.dumps({'prompt': prompt, 'variables': program_variables.variable_values})}"
        await self.response.send(chunk)

async def serve(request: aiohttp.web_request.Request, q: LMQLQueryFunction, *args, output_writer_cls=EventStreamOutputWriter, **kwargs):
    """
    Runs the given query with *args and **kwargs, and streams query output 
    to a SSE client, connected via the given request.
    """
    async with sse_response(request) as resp:
        async def runner():
            try:
                await resp.send("START")
                await q(output_writer=output_writer_cls(resp))
                await resp.send("DONE")
            except Exception as e:
                if not resp.ended:
                    await resp.send("ERROR " + str(e))
        await runner()

def endpoint(query, *args, output_writer_cls=EventStreamOutputWriter, **kwargs):
    """
    Returns a web handler that runs the given query with *args and **kwargs, 
    and streams query output to a SSE client.
    """
    q = lmql.query(query)
    async def handler(request):
        return await serve(request, q, *args, output_writer_cls=output_writer_cls, **kwargs)
    return handler