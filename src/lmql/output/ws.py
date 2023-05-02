import asyncio
import lmql

from lmql.runtime.output_writer import BaseOutputWriter
import json

try:
    import aiohttp
    from aiohttp import web
except ImportError:
    raise ImportError("To use LMQL's websocket output, you must install aiohttp. Try: pip install aiohttp")

class WebSocketOutputWriter(BaseOutputWriter):
    """
    An output writer that sends the output to a websocket.
    """

    def __init__(self, socket):
        super().__init__(allows_input=False)
        self.socket = socket

    async def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables):
        await self.socket.send_str(json.dumps({
            "prompt": prompt,
            "variables": program_variables.variable_values
        }))

async def serve(request: aiohttp.web_request.Request, q: lmql.LMQLQueryFunction, *args, output_writer_cls=WebSocketOutputWriter, **kwargs):
    """
    Receives LMQL query code via websockets, compiles it, runs it
    and streams the output back to the client.
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    query_task = None

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                # run the query
                async def runner():
                    await ws.send_str("START")
                    await q(output_writer=WebSocketOutputWriter(ws))
                    await ws.send_str("DONE")
                query_task = asyncio.create_task(runner())
        
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('lmql websocket connection closed with exception %s' % ws.exception())

    if query_task is not None:
        query_task.cancel()
        await query_task
    
    return ws

def endpoint(query, *args, output_writer_cls=WebSocketOutputWriter, **kwargs):
    """
    Returns a aiohttp web handler that runs the given query with *args and **kwargs, 
    and streams query output via websockets.
    """
    # pre-compile the query
    q = lmql.query(query)

    async def handler(request):
        return await serve(request, q, *args, output_writer_cls=output_writer_cls, **kwargs)
    return handler