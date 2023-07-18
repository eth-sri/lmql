# setup to use lmql submodule
import os
import sys
import io
import json
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')

import asyncio
from aiohttp import web
import lmql
from lmql.runtime.bopenai import get_stats
from lmql.runtime.output_writer import BaseOutputWriter

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))

def handle(request):
    index = open(os.path.join(PROJECT_DIR, 'assets/index.html')).read()
    return web.Response(text=index, content_type='text/html')

def studio(request):
    index = open(os.path.join(PROJECT_DIR, 'assets/studio.html')).read()
    return web.Response(text=index, content_type='text/html')

# serve chat_assets/ folder
def assets(request):
    path = request.match_info.get('path', '')
    # relative to this ../assets/ folder
    assert path.startswith('chat_assets/'), path
    path = path.replace('chat_assets/', PROJECT_DIR + '/assets/')
    return web.FileResponse(path)

class websocket_executor(BaseOutputWriter):
    def __init__(self, query, ws):
        self.user_input_fut = None
        self.ws = ws
        self.chatbot_task = asyncio.create_task(self.error_handling_query_call(query), name='chatbot query')
        self.message_id = 0

    async def error_handling_query_call(self, query):
        try:
            await query(output_writer=self)
        except Exception as e:
            print("error in chatbot query", flush=True)
            import traceback
            traceback.print_exc()
            await self.ws.send_str(json.dumps({
                "type": "error",
                "message": str(e)
            }))
            await self.ws.close()

    async def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables): 
        chunk = json.dumps({
            "type": "response",
            "message_id": self.message_id - (1 if variable != "ANSWER" else 0),
            "data": {
                'prompt': prompt, 
                'variables': program_variables.variable_values
            }
        })

        await self.ws.send_str(chunk)

    async def input(self, *args):
        if self.user_input_fut is not None:
            return await self.user_input_fut
        else:
            self.user_input_fut = asyncio.get_event_loop().create_future()
            self.message_id += 1
            return await self.user_input_fut

class chatter:
    def __init__(self, file, port=8089):
        self.port = port
        self.file = file

        self.executors = []

    async def handle_websocket_chat(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        with open(self.file) as f:
            source = f.read()
            try:
                chatbot = lmql.query(source)
            except Exception as e:
                import traceback
                await ws.send_str(json.dumps({
                    "type": "error",
                    "message": str(e) + "\n\n" + traceback.format_exc()
                }))
                ws.close()
                return ws

        chat_executor = websocket_executor(chatbot, ws)
        self.executors.append(chat_executor)
        
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    data = json.loads(msg.data)
                    if data["type"] == "input":
                        if chat_executor.user_input_fut is not None:
                            fut = chat_executor.user_input_fut
                            chat_executor.user_input_fut = None
                            fut.set_result(data["text"])
                        else:
                            print("warning: got input but query is not waiting for input", flush=True)
            elif msg.type == web.WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                    ws.exception())
        chat_executor.chatbot_task.cancel()

        if chat_executor in self.executors:
            self.executors.remove(chat_executor)
        print("websocket connection closed", len(self.executors), "executors left", flush=True)
        return ws

    async def source(self, request):
        # serves self.chatbot lmql source
        source = open(self.file).read()
        source = self.file + "\n" + source
        return web.Response(text=source, content_type='text/plain')

    async def post_source(self, request):
        source = await request.text()

        for e in self.executors: 
            await e.ws.close()
        self.executors = []
            
        errorout = sys.stderr
        try:    
            sys.stderr = io.StringIO()
            test = lmql.query(source)
        except Exception as e:
            error = sys.stderr.getvalue() + str(e)
            return web.Response(text=error, content_type='text/plain')
        finally:
            sys.stderr = errorout

        with open(self.file, 'w') as f:
            f.write(source)


        return web.Response(text='ok', content_type='text/plain')

    async def main(self):
        app = web.Application()
        
        # host index.html
        app.add_routes([web.get('/', handle)])

        # host studio.html
        app.add_routes([web.get('/studio', studio)])

        # 
        app.add_routes([web.get('/source', self.source)])
        app.add_routes([web.post('/source', self.post_source)])
        
        # host chatbot query
        # websocket connection
        app.add_routes([web.get('/chat', self.handle_websocket_chat)])

        # host chat_assets/ folder
        app.add_routes([web.get('/{path:.*}', assets)])
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        print('🤖 Your LMQL chatbot is waiting for you at http://localhost:{}'.format(self.port), flush=True)
        
        # open browser if possible
        import webbrowser
        webbrowser.open('http://localhost:{}'.format(self.port))
        
        while True:
            await asyncio.sleep(3600)

    def run(self):
        asyncio.run(self.main())