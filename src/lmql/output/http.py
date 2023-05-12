import lmql

from lmql.runtime.output_writer import BaseOutputWriter
from lmql import LMQLQueryFunction
import json

try:
    import aiohttp
    from aiohttp import web
except ImportError:
    raise ImportError("To use LMQL's http output writer, you must install aiohttp. Try: pip install aiohttp")

class HttpEventStreamOutputWriter(BaseOutputWriter):
    def __init__(self, response):
        super().__init__(allows_input=False)
        self.response = response
    
    async def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables):
        chunk = f"{json.dumps({'prompt': prompt, 'variables': program_variables.variable_values})}"
        await self.response.write(("data: " + chunk + "\n").encode("utf-8"))
        await self.response.drain()

async def serve(request: aiohttp.web_request.Request, q: LMQLQueryFunction, *args, output_writer_cls=HttpEventStreamOutputWriter, **kwargs):
    """
    Runs the given query with *args and **kwargs, and streams query output 
    to a SSE client, connected via the given request.
    """
    resp = web.Response()
    resp.content_type = "text/event-stream"

    resp.enable_chunked_encoding()
    await resp.prepare(request)
    
    async def runner():
        try:
            await resp.write("data: START\n".encode("utf-8"))
            await q(*args, output_writer=output_writer_cls(resp), **kwargs)
            await resp.write("data: DONE\n".encode("utf-8"))
        except Exception as e:
            await resp.write(("ERROR " + str(e)).encode("utf-8"))
    
    await runner()

def endpoint(query, *args, output_writer_cls=HttpEventStreamOutputWriter, **kwargs):
    """
    Returns a web handler that runs the given query with *args and **kwargs, 
    and streams query output to a SSE client.
    """
    q = lmql.query(query)
    async def handler(request):
        nonlocal kwargs
        
        payload = {}
        # get post data
        if request.method == "POST":
            payload = await request.json()
        # get query parameters
        elif request.method == "GET":
            payload = request.query

        query_kwargs = {**payload, **(kwargs.copy())}

        return await serve(request, q, *args, output_writer_cls=output_writer_cls, **query_kwargs)
    return handler