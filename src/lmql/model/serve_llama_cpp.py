"""
Serves a transformers model as LMQL inference API.
"""

from dataclasses import dataclass, field
from collections import defaultdict

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from multiprocessing import Queue as MPQueue
from queue import Empty
from queue import Queue
import multiprocessing
from typing import Dict
import atexit
import argparse
import time
from llama_cpp.llama import Llama, llama_cpp
import inspect

@dataclass
class InferenceServerState:
    model_identifier : str
    tokenizer_descriptor : str
    dtype: str

    queue: Queue
    tokenize_queue: Queue
    all_results_queue : Queue
    
    sample_count: int = 0
    client_results_queues: Dict[str,Queue] = field(default_factory=dict)
    
    exit: bool = False

class TokenizerProcessor:
    def __init__(self, state: InferenceServerState, processor: "ModelProcessor"):
        self.model_identifier = state.tokenizer_descriptor
        self.model = processor
        self.queue = state.tokenize_queue
        self.state = state

    def shutdown(self):
        self.state.exit = True

    def tokenize(self, tokenizer, sample_id, client_id, item):
        text = item["text"]

        if text == "<EOS>":
            input_ids = [tokenizer.token_eos()]
        elif text == "<BOS>":
            input_ids = [tokenizer.token_bos()]
        else:
            input_ids = tokenizer.tokenize(b" " + text.encode("utf-8"))

        self.state.all_results_queue.put({
            "sample_id": sample_id,
            "client_id": client_id,
            "input_ids": input_ids
        })

    def detokenize(self, tokenizer, sample_id, client_id, item):
        input_ids = item["input_ids"]

        text = tokenizer.detokenize(input_ids).decode('utf-8')
        self.state.all_results_queue.put({
            "sample_id": sample_id,
            "client_id": client_id,
            "text": text
        })

    def run(self):
        # load tokenizer
        tokenizer = self.model
        print("Tokenizer {} ready!".format(self.model_identifier))

        while not self.state.exit:
            item = self.queue.get()
            if item is None:
                time.sleep(0.1)
                continue

            sample_id = item["sample_id"]
            client_id = item["client_id"]
            action = item["action"]

            if action == "tokenize":
                self.tokenize(tokenizer, sample_id, client_id, item)
            elif action == "detokenize":
                self.detokenize(tokenizer, sample_id, client_id, item)
            else:
                print("error: unknown TokenizerProcessor action {}".format(action))
        
        print("Tokenizer shut down.")

class ModelProcessor:
    def __init__(self, state: InferenceServerState, llama_kwargs: dict, cache: str = None):
        self.model_identifier = state.model_identifier
        self.llama_kwargs = llama_kwargs
        self.queue = state.queue
        self.state = state
        
        self.cache = None
        if cache is not None:
            from rocksdict import Rdict
            self.cache = Rdict(cache)
            
        self.request_count = 0
        self.requests_cached = 0
        self.last_report = time.time()
        self.last_request_count = 0
    

    def shutdown(self):
        self.state.exit = True
    
    def __del__(self):
        if self.cache is not None:
            self.cache.close()
        
    def print_stats(self):
        # fancy unicode based terminal spinner
        terminal_spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        throughput = (self.request_count - self.last_request_count) / (time.time() - self.last_report)
        self.last_report = time.time()
        self.last_request_count = self.request_count
        
        # format throughput to two decimal places
        print("{} {:.2f} calls/s, Requests Served: {}, Queue: {}".format(
            terminal_spinner_chars[self.request_count % len(terminal_spinner_chars)], 
            throughput,
            self.request_count, 
            self.state.queue.qsize()), end="\r")

    def run(self):

        
        # load model
        print("Loading {} (CPU)".format(self.model_identifier))
        self.model = Llama(**{**self.llama_kwargs, 'logits_all': True})

        print("Ready!".format(self.model_identifier))

        while not self.state.exit:
            self.print_stats()
            # wait for self.queue to have an item
            try:
                item = self.queue.get(timeout=1.0)
            except Empty:
                continue
            except KeyboardInterrupt:
                break

            if item is None: 
                time.sleep(0.1)
                continue

            self.request_count += 1
        


            sample_id = item["sample_id"]
            client_id = item["client_id"]
            input_ids = item["input_ids"]

            if self.cache is not None:
                key = str(input_ids)
                if key in self.cache:
                    self.requests_cached += 1
                    self.state.all_results_queue.put({
                        "client_id": client_id,
                        "sample_id": sample_id,
                        "next_token_logits": self.cache[key]
                    })
                    continue
            
            res = self.model.eval(input_ids)
            
            next_token_logits = self.model.all_logits[-1]
            
            if self.cache is not None:
                key = str(input_ids.tolist())
                self.cache[key] = next_token_logits.tolist()

            self.state.all_results_queue.put({
                "client_id": client_id,
                "sample_id": sample_id,
                "next_token_logits": next_token_logits.detach().tolist()
            })
        
        print("Processor shut down")


class LMQLInferenceAPIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._client_id = None
        super().__init__(*args, **kwargs)

    # disable logging
    def log_message(self, format, *args):
        return

    @property
    def state(self) -> InferenceServerState:
        return self.server.state
    
    @property
    def client_id(self) -> str:
        if self._client_id is None:
            self.error_bad_request(msg="client_id not set (please provide the client_id in POST payload or in query.")
            raise Exception("client_id not set")
        return self._client_id

    def error_bad_request(self, msg="Bad request."):
        self.send_response(400)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(msg.encode("utf-8"))

    def process_some_all_results(self, max=10):
        all_results_queue = self.state.all_results_queue
        i = 0
        
        while not all_results_queue.empty() and i < max:
            result = all_results_queue.get()

            result_client_id = result["client_id"]
            
            if result_client_id not in self.state.client_results_queues:
                self.state.client_results_queues[result_client_id] = Queue()
            self.state.client_results_queues[result_client_id].put(result)

            i += 1

    def do_GET_results(self):
        request_client_id = self.path.split("/")[2]
        self._client_id = f"{self.client_address[0]}-{request_client_id}"

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # process some results from the model and group them by client_id
        self.process_some_all_results()

        if self.client_id not in self.state.client_results_queues.keys():
            self.wfile.write(b'[]')
            return

        # return all results for self.client_id currently available
        self.wfile.write("[".encode())
        while not self.state.client_results_queues[self.client_id].empty():
            result = self.state.client_results_queues[self.client_id].get()
            self.wfile.write(json.dumps(result).encode())
            
            # omit last colon
            if self.state.client_results_queues[self.client_id].empty(): break
            else: self.wfile.write(b",")
        self.wfile.write(b"]")

    def do_queue_forward(self, payload, sample_id):
        try: 
            input_ids = payload['input_ids']
            attention_mask = payload.get('attention_mask', None)
            model_identifier = payload['model_identifier']

            if model_identifier != self.state.model_identifier:
                self.error_bad_request("The inference API serves model {} not {}.".format(self.state.model_identifier, model_identifier))
                return

            self._client_id = f"{self.client_address[0]}-{payload['client_id']}"

            assert type(input_ids) == list # and all([type(i) == int for i in input_ids])

            self.state.queue.put({
                'client_id': self.client_id,
                'sample_id': sample_id,
                'input_ids': input_ids,
                'attention_mask': attention_mask
            })

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'sample_id': sample_id}).encode())
        except Exception as e: 
            self.error_bad_request()

    def do_queue_tokenize(self, payload, sample_id):
        try: 
            text = payload['text']
            self._client_id = f"{self.client_address[0]}-{payload['client_id']}"

            assert type(text) == str

            self.state.tokenize_queue.put({
                'client_id': self.client_id,
                'sample_id': sample_id,
                'action': 'tokenize',
                'text': text
            })

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'sample_id': sample_id}).encode())
        except Exception as e: 
            self.error_bad_request()
        
    def do_queue_detokenize(self, payload, sample_id):
        try: 
            input_ids = payload['input_ids']
            self._client_id = f"{self.client_address[0]}-{payload['client_id']}"

            assert type(input_ids) == list and all([type(i) == int for i in input_ids])

            self.state.tokenize_queue.put({
                'client_id': self.client_id,
                'sample_id': sample_id,
                'action': 'detokenize',
                'input_ids': input_ids
            })

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'sample_id': sample_id}).encode())
        except Exception as e: 
            self.error_bad_request()

    def do_POST_queue(self):
        # handle POST to /queue
        payload = self.rfile.read(int(self.headers['Content-Length']))
        payload = json.loads(payload)
        # get client address and port
        sample_id = payload["sample_id"]

        action = payload['action']

        if action == "forward":
            self.do_queue_forward(payload, sample_id)
        elif action == "tokenize":
            self.do_queue_tokenize(payload, sample_id)
        elif action == "detokenize":
            self.do_queue_detokenize(payload, sample_id)
        else:
            self.error_bad_request("Unknown action: {}".format(action))

    def do_POST(self):
        if self.path == "/queue":
            self.do_POST_queue()
            return
        else:
            self.send_error(404)
            return

    def do_GET(self):
        if self.path.startswith("/results"):
            self.do_GET_results()
            return
        else:
            self.send_error(404)
            return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=str)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--cache", type=str, default=None)
    llama_kwargs = {}
    sig = inspect.signature(Llama.__init__)
    for name, param in sig.parameters.items():
        if name == 'self':
            continue
        llama_kwargs[name] = None
        if param.default == inspect.Parameter.empty:
            parser.add_argument(name)
        else:
            parser.add_argument(f'--{name}', default=param.default) 

    args = parser.parse_args()
    
    llama_kwargs = {kwarg: getattr(args, kwarg) for kwarg in llama_kwargs.keys()}
    
    manager = multiprocessing.Manager()
    
    # prepare configuration
    model_descriptor = args.model
    state = InferenceServerState(model_descriptor, 
                                 model_descriptor, 
                                 "", 
                                 queue=manager.Queue(), 
                                 tokenize_queue=manager.Queue(),
                                 all_results_queue=manager.Queue())

    # run model in separate process
    processor = ModelProcessor(state, cache=args.cache, llama_kwargs=llama_kwargs)
    processor.run()

    # run tokenizers in separate process
    tokenizer_processor = TokenizerProcessor(state, processor)
    tokenizer_processor.run()

    # run inference API server in this process
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, LMQLInferenceAPIHandler)
    httpd.state = state
    
    try:
        print("Serving LMQL inference API on {}:{}".format(args.host, args.port))
        httpd.serve_forever()
    except KeyboardInterrupt:
        # terminate server
        httpd.shutdown()
        httpd.server_close()
        print("Server stopped")

    # terminate processors
    processor.shutdown()
    tokenizer_processor.shutdown()
