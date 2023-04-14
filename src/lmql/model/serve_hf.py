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
from typing import Dict, Tuple
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
from lmql.model.serve_types import TokenizerProcessor, ModelProcessor, InferenceServerState

class HFTokenizerProcessor(TokenizerProcessor):

    def tokenize(self, tokenizer, sample_id, client_id, item):
        text = item["text"]

        if text == "<EOS>":
            input_ids = [tokenizer.eos_token_id]
        elif text == "<BOS>":
            input_ids = [tokenizer.bos_token_id]
        else:
            input_ids = tokenizer(text)["input_ids"]

        self.state.all_results_queue.put({
            "sample_id": sample_id,
            "client_id": client_id,
            "input_ids": input_ids
        })

    def detokenize(self, tokenizer, sample_id, client_id, item):
        input_ids = item["input_ids"]

        text = tokenizer.decode(input_ids)
        self.state.all_results_queue.put({
            "sample_id": sample_id,
            "client_id": client_id,
            "text": text
        })

    def run(self, index):
        # load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.model_identifier)
        print("Tokenizer #{} {} ready!".format(index, self.model_identifier))

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
        
        print("Tokenizer #{} shut down.".format(index))

class HFModelProcessor(ModelProcessor):

    def run(self):
        dtype = self.state.dtype
        if dtype == "float16":
            dtype = torch.float16
        else:
            dtype = None
        
        # load model
        if not self.cuda:
            print("Loading {} (CPU)".format(self.model_identifier))
            self.model = AutoModelForCausalLM.from_pretrained(self.model_identifier, torch_dtype=dtype, resume_download=True)
        else:
            print("Loading {} (Multi-GPU)".format(self.model_identifier))
            self.model = AutoModelForCausalLM.from_pretrained(self.model_identifier, torch_dtype=dtype, resume_download=True, device_map="auto")
        self.model.eval()
        
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
        
            device = "cuda" if self.cuda else "cpu"

            sample_id = item["sample_id"]
            client_id = item["client_id"]
            input_ids = torch.tensor(item["input_ids"], dtype=torch.long).to(device)
            attention_mask = item.get("attention_mask", None)
            
            if attention_mask is None:
                attention_mask = torch.ones_like(input_ids).to(device)
            else:
                attention_mask = torch.tensor(attention_mask, dtype=torch.long).to(device)

            if self.cache is not None:
                key = "IDs:" + str(input_ids.tolist()) + " MASK:" + str(attention_mask.tolist())
                if key in self.cache:
                    self.requests_cached += 1
                    self.state.all_results_queue.put({
                        "client_id": client_id,
                        "sample_id": sample_id,
                        "next_token_logits": self.cache[key]
                    })
                    continue
            
            res = self.model.forward(input_ids=input_ids, attention_mask=attention_mask)
            
            if input_ids.ndimension() == 2:
                next_token_logits = res.logits[:,-1]
            else:
                next_token_logits = res.logits[-1]
            
            if self.cache is not None:
                key = "IDs:" + str(input_ids.tolist()) + " MASK:" + str(attention_mask.tolist())
                self.cache[key] = next_token_logits.tolist()

            self.state.all_results_queue.put({
                "client_id": client_id,
                "sample_id": sample_id,
                "next_token_logits": next_token_logits.detach().tolist()
            })
        
        print("Processor shut down")
        



def get_serve(state: InferenceServerState, args: argparse.Namespace)->Tuple[ModelProcessor, TokenizerProcessor]:
    # run model in separate process
    processor = HFModelProcessor(state, cuda=args.cuda, cache=args.cache)
    processor.run_in_parallel()

    # run tokenizers in separate process
    tokenizer_processor = HFTokenizerProcessor(state)
    tokenizer_processor.run_in_parallel(n=args.num_tokenizer_processes)
    return processor, tokenizer_processor

def add_parser(base_parser):
    ...

