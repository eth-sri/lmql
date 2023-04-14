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
from typing import Dict, Optional
import requests
import asyncio
import sys
import atexit
import argparse
import time
import os
import subprocess

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
from abc import ABC, abstractmethod

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

    
class TokenizerProcessor(ABC):
    def __init__(self, state: InferenceServerState):
        self.model_identifier = state.tokenizer_descriptor
        self.queue = state.tokenize_queue
        self.state = state

    def shutdown(self):
        self.state.exit = True
        
    @abstractmethod
    def tokenize(self, tokenizer, sample_id, client_id, item):
        """Tokenize item input"""

    @abstractmethod
    def detokenize(self, tokenizer, sample_id, client_id, item):
        """Detokenize item input"""
    
    @abstractmethod
    def run(self, index):
        """Evaluate items from the queue"""

    def run_in_parallel(self, n=2):
        atexit.register(self.shutdown)
        
        workers = []

        for i in range(n):
            p = multiprocessing.Process(target=self.run, args=(i,))
            p.start()
            workers.append(p)
        
        return workers

class ModelProcessor(ABC):
    def __init__(self, state: InferenceServerState, cuda: bool = False, cache: Optional[str] = None):
        self.model_identifier = state.model_identifier
        self.queue = state.queue
        self.state = state
        self.cuda = cuda
        
        self.cache = None
        if cache is not None:
            from rocksdict import Rdict
            self.cache = Rdict(cache)
            
        self.request_count = 0
        self.requests_cached = 0
        self.last_report = time.time()
        self.last_request_count = 0
        
        try:
            self.nvidia_logging = subprocess.Popen(["nvidia-smi"], stdout=subprocess.PIPE).wait() == 0
        except:
            self.nvidia_logging = False

    def shutdown(self):
        self.state.exit = True
    
    def __del__(self):
        if self.cache is not None:
            self.cache.close()
        
    def print_stats(self):
        if self.nvidia_logging:
            visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES", None)
            cmds = ["nvidia-smi"]
            if visible_devices is not None:
                cmds.append("-i={}".format(visible_devices))
            cmds += ["--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"]
            output = [l.split(", ") for l in subprocess.check_output(cmds).decode("utf-8").split("\n") if l.strip() != ""]
            gpu_usage = ["GPU {} {}, util {}".format(i, row[1] + "/" + row[2], row[3]) for i, row in enumerate(output)]
        else:
            gpu_usage = ["GPU monitoring not available on non-CUDA systems"]
        
        print(" " * 100, end="\r")
        # fancy unicode based terminal spinner
        terminal_spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        throughput = (self.request_count - self.last_request_count) / (time.time() - self.last_report)
        self.last_report = time.time()
        self.last_request_count = self.request_count
        
        # format throughput to two decimal places
        print("{} {:.2f} calls/s, Requests Served: {}, Queue: {} [{}]".format(
            terminal_spinner_chars[self.request_count % len(terminal_spinner_chars)], 
            throughput,
            self.request_count, 
            self.state.queue.qsize(), 
            ", ".join(gpu_usage)), end="\r")

    @abstractmethod
    def run(self):
        """Infer on the queue"""

    def oom_reloading_run(self):
        while True:
            try:
                self.run()
                return
            except RuntimeError as e:
                if "CUDA out of memory" in str(e):
                    print("Crashed due to OOM, reloading model.")
                    continue
                else:
                    import traceback
                    traceback.print_exc()
                    print("Crashed with", e, "reloading model...")
                    continue

    def run_in_parallel(self):
        atexit.register(self.shutdown)

        p = multiprocessing.Process(target=self.oom_reloading_run)
        p.start()
        return p

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