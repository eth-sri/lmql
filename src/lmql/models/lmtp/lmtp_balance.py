"""
Simple reverse proxying load balancer for multiple LMTP endpoints.
"""

from .lmtp_inference_server import *
from .utils import rename_model_args
import random

class LMTPBalancer:
    def __init__(self, workers):
        self.workers = workers
        self.active_connections = {w: 0 for w in workers}

    def worker(self):
        # sort workers by number of active connections
        sorted_workers = sorted(self.workers, key=lambda w: self.active_connections[w])
        
        # select random among workers with least active connections
        sorted_workers = [w for w in sorted_workers if self.active_connections[w] == self.active_connections[sorted_workers[0]]]
        worker = random.choice(sorted_workers)
        
        # select worker with least active connections
        return LMTPWorkerHandle(worker, self)

class LMTPWorkerHandle:
    def __init__(self, endpoint, balancer):
        self.endpoint = endpoint
        self.balancer = balancer

    async def __aenter__(self):
        self.balancer.active_connections[self.endpoint] += 1
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        self.balancer.active_connections[self.endpoint] = max(0, self.balancer.active_connections[self.endpoint] - 1)

def lmtp_balance(workers, host, port):
    """
    CLI for starting an LMTP load balancer for a given list of worker endpoints.
    """
    balancer = LMTPBalancer(workers)

    # stream endpoint
    async def stream(request):
        # bidirectional websocket 
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        worker_ws_connection = None

        # select worker
        async with balancer.worker() as worker:
            # proxy connection client <-> worker
            try:
                async with aiohttp.ClientSession() as session:
                    # start websocket session with / endpoint
                    async with session.ws_connect("ws://" + worker.endpoint) as worker_ws:
                        worker_ws_connection = worker_ws
                        
                        async def worker_to_client():
                            async for msg in worker_ws:
                                if msg.type == aiohttp.WSMsgType.TEXT:
                                    await ws.send_str(msg.data)
                                elif msg.type == aiohttp.WSMsgType.ERROR:
                                    ws.close()
                                    break
                        async def client_to_worker():
                            async for msg in ws:
                                if msg.type == aiohttp.WSMsgType.TEXT:
                                    await worker_ws.send_str(msg.data)
                                elif msg.type == aiohttp.WSMsgType.ERROR:
                                    worker_ws.close()
                                    break
                        
                        done, pending = await asyncio.wait([worker_to_client(), client_to_worker()], return_when=asyncio.FIRST_COMPLETED)
                        for task in pending:
                            task.cancel()
            # handle ConnectionResetError
            except ConnectionResetError:
                pass
            except Exception as e:
                print(f"balancer: {e}")
                import traceback
                traceback.print_exc()
            finally:
                if worker_ws_connection is not None:
                    await worker_ws_connection.close()
                await ws.close()

    if len(workers) < 1:
        raise ValueError("Must specify at least one worker endpoint.")

    app = web.Application()
    app.add_routes([web.get('/', stream)])
    
    def web_print(*args):
        if len(args) == 1 and args[0].startswith("======== Running on"):
            print(f"[Serving LMTP balancer on ws://{host}:{port}/]")
            print(f"Workers: {workers}")
        else:
            print(*args)

    # executor
    tasks = [web._run_app(app, host=host, port=port, print=web_print)]
    asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

def balance_main(args):
    workers = []
    
    # extract --port and --host from workers
    host = "localhost"
    port = 8080
    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "--port":
            port = int(args[i+1])
            i += 2
        elif arg == "--host":
            host = args[i+1]
            i += 2
        else:
            workers.append(arg)
            i += 1
    
    lmtp_balance(workers, host=host, port=port)

if __name__ == "__main__":
    balance_main(sys.argv[1:])