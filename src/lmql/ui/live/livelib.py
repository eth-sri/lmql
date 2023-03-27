import sys
import json
import asyncio
import inspect

def send(*args):
    print(*args)
    sys.stdout.flush()

class LiveApp:
    def __init__(self, name, fct, client_script=None, client_html=None):
        self.name = name
        self.fct = fct

        if client_script is not None:
            with open(client_script, "r") as f:
                self.client_script = f.read()
        else:
            self.client_script = None

        if client_html is not None:
            with open(client_html, "r") as f:
                self.html = f.read()
        else:
            self.html = None

    def __repr__(self) -> str:
        return "<LiveApp: {}>".format(self.name)

    @staticmethod
    def kill():
        LiveApp.interrupt = True


    @staticmethod
    async def ainput(string: str = "", web=False) -> str:
        # on the web, we do not have stdin and use a custom input mechanism
        if web:
            fut = asyncio.get_event_loop().create_future()
            LiveApp.stdin_queue.put_nowait(fut)
            return await fut
        return (await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline)).rstrip("\n")

    @staticmethod
    async def send_input(data):
        try:
            fut = LiveApp.stdin_queue.get_nowait()
            fut.set_result(data)
        except asyncio.QueueEmpty:
            raise Exception("No input request pending")
    
    @staticmethod
    def cli():
        return asyncio.run(LiveApp.async_cli())

    @staticmethod
    async def async_cli(args=None):
        if args is None:
            args = sys.argv

        if "endpoints" in set(args):
            for name,app in LiveApp.endpoint.items():
                print(app.name)
        elif "client-script" in set(args):
            app_name = args[2]
            for name,app in LiveApp.endpoint.items():
                if app.name == app_name:
                    if app.client_script is not None: 
                        print(app.client_script)
                    else: 
                        print("")
        elif "client-html" in set(args):
            app_name = args[2]
            for name,app in LiveApp.endpoint.items():
                if app.name == app_name:
                    if app.html is not None: 
                        print(app.html)
                    else: 
                        print("")
        else:
            endpoint = LiveApp.endpoint[args[1]]
            input = json.loads(args[2])
            endpoint_args = json.loads(args[3])
            
            # check if fct has kwarg web
            if args[0] == "web" and "web" in inspect.signature(endpoint.fct).parameters:
                kwargs = {"web": True}
            else:
                kwargs = {}
            
            result = await endpoint.fct(input, *endpoint_args, **kwargs)
            if result is not None: print(result)

LiveApp.endpoint = {}
LiveApp.stdin_queue = asyncio.Queue()
LiveApp.interrupt = False

class Int64JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, int):
            return int(obj)
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)

def add_debugger_output(type_identifier: str, json_encodable_dict: dict):
    data = {
        "type": type_identifier,
        "data": json_encodable_dict
    }
    payload = json.dumps(data, cls=Int64JSONEncoder)
    
    print("DEBUGGER OUTPUT", payload.replace("\n", "\\n"), flush=True)

# live annotation registers a function with LiveApp.endpoint
# annotation arguments are also functions 'input' and 'output'
def live(client_script=None, client_html=None):
    def func_transformer(f):
        LiveApp.endpoint[f.__name__] = LiveApp(f.__name__, f, client_script=client_script, client_html=client_html)
        return f
    return func_transformer