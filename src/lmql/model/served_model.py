import asyncio
from dataclasses import dataclass
from typing import Optional
import requests
import os
import torch
import time
import sys
import warnings
from tqdm import tqdm
from transformers import BeamScorer, LogitsProcessorList, PretrainedConfig, StoppingCriteriaList

from lmql.model.async_generation_utils import GenerationMixin

from lmql.utils import nputil
import numpy as np

class ServedModel:
    def __init__(self, host, model_identifier, timeout=60, use_tq=True, local=False):
        self.host = host
        
        self.model_identifier = model_identifier
        self.pending = {}
        self.polling_interval = 0.05
        self.timeout = timeout
        
        if local:
            from .local_client import LocalClient
            self.local_client = LocalClient(model_identifier)
        else:
            self.local_client = None

        # derive client_id from process id
        self.client_id = f"{os.getpid()}:{id(self)}"

        self.result_process_running = False

        if use_tq: 
            assert False
            self.tq = tqdm(desc="Querying model...", unit="tok")
        else: 
            self.tq = None

        self.sample_id = 0

        # track number of consumed tokens, queries (forward) and generate calls
        self.consumed_tokens = 0
        self.num_queries = 0
        self.num_generate_calls = 0
        self.billable_tokens = 0

    def report_stats(self, printer, decoder_step=None):
        if printer is None:
            return
        if hasattr(printer, "report_model_stats"):
            data = {
                "tokens": self.billable_tokens,
                "model": self.model_identifier
            }
            if decoder_step is not None:
                data["_step"] = decoder_step
            printer.report_model_stats(**data)

    def create_result_processor_task_if_required(self):
        if self.result_process_running: 
            return
        
        loop = asyncio.get_event_loop()
        loop.create_task(self.result_processor())
        self.result_process_running = True

    def process_result(self, result):
        # check if torch is available
        if "next_token_logits" in result:
            result["next_token_logits"] = torch.tensor(result["next_token_logits"])
        if "input_ids" in result:
            result["input_ids"] = result["input_ids"]
        
        if "next_token_logits" in result:
            if result["next_token_logits"].dim() == 2:
                if self.tq is not None: 
                    self.tq.update(result["next_token_logits"].shape[0])
            else:
                if self.tq is not None: 
                    self.tq.update(1)

    async def result_processor(self):
        loop = asyncio.get_event_loop()

        while True:
            start_time = time.time()
            
            results = await loop.run_in_executor(None, requests.get, f"{self.host}/results/{self.client_id}")
            results = results.json()
            
            # process results
            for result in results:
                sample_id = result['sample_id']
                if sample_id in self.pending:
                    self.process_result(result)
                    self.pending[sample_id].set_result(result)
                    del self.pending[sample_id]
                else:
                    print("warning: result for unknown sample_id {}".format(sample_id), self.pending)

            remaining_sleep_time = self.polling_interval - (time.time() - start_time)
            if remaining_sleep_time > 0: await asyncio.sleep(remaining_sleep_time)

    def _timeout(self, sample_id):
        if sample_id in self.pending:
            self.pending[sample_id].set_exception(TimeoutError("Timed out waiting for result of sample {}".format(sample_id)))
            del self.pending[sample_id]

    def reset_stats(self):
        self.consumed_tokens = 0
        self.num_queries = 0

    def forward(self, input_ids, attention_mask=None):
        assert input_ids.numel() > 0, "input_ids must not be empty"
        # keep stats
        num_input_tokens = sum(len(x) for x in input_ids)
        self.consumed_tokens = self.consumed_tokens + num_input_tokens
        self.billable_tokens += 1

        assert input_ids.dtype == torch.long, "input_ids must be of dtype torch.long"
        # count prompt tokens + 1 generated output token per sequence
        
        # use local client if hosted in process
        if self.local_client is not None:
            return self.local_client.forward(input_ids, attention_mask)

        self.create_result_processor_task_if_required()

        loop = asyncio.get_event_loop()

        # # handle torch tensors
        if type(input_ids) is torch.Tensor:
            input_ids = input_ids.tolist()

        sample_id = self.sample_id
        self.sample_id += 1

        payload = {
            "action": "forward",
            "input_ids": input_ids,
            **{"attention_mask": attention_mask.tolist() if attention_mask is not None else None},
            "model_identifier": self.model_identifier,
            "client_id": self.client_id,
            "sample_id": sample_id
        }

        try:
            assert sample_id not in self.pending, "sample_id {} already in self.pending".format(sample_id)
            # setup future and timeout
            self.pending[sample_id] = loop.create_future()
            
            r = requests.post(f"{self.host}/queue", json=payload)
            
            if r.status_code != 200:
                raise Exception(f"Error posting to {self.host}/queue: {r.status_code}, {r.text}")
            
            loop.call_later(self.timeout, self._timeout, sample_id)
            
            return self.pending[sample_id]
        except requests.exceptions.ConnectionError as e:
            # check for connection refused
            if "Connection refused" in str(e):
                raise Exception(f"Error connecting to {self.host}/queue. Please make sure an instance of the LMQL inference API for this model is running. To start it, run `python -m serve <MODEL>`.")
            else:
                raise e

@dataclass
class ServedPretrainedModelOutput:
    logits: torch.Tensor

    # enable 'in' operator
    def __contains__(self, item):
        return item in self.__dict__.keys()

class ServedPretrainedModel(ServedModel, GenerationMixin):
    def __init__(self, host, model_identifier, timeout=60, use_tq=False, model_kwargs=None, local=False):
        super().__init__(host, model_identifier, timeout, use_tq=use_tq, local=local)

        self.model_kwargs = model_kwargs or {}
        
        self.config = PretrainedConfig()
        self.device = torch.device("cpu")

        # old context model
        self.previous_context_model = None

    async def __call__(self, input_ids: torch.Tensor, *args, **kwargs):
        res = await self.forward(input_ids, attention_mask=kwargs.get("attention_mask", None))
        logits = res["next_token_logits"]

        return ServedPretrainedModelOutput(logits.unsqueeze(1))

    async def __aenter__(self):
        self.previous_context_model = ServedPretrainedModel.context_model

        bos_token_id = (await self.tokenize("<BOS>"))[0]
        setattr(self, "bos_token_id", bos_token_id)
        eos_token_id = (await self.tokenize("<EOS>"))[0]
        setattr(self, "eos_token_id", eos_token_id)

        ServedPretrainedModel.context_model = self
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        ServedPretrainedModel.context_model = self.previous_context_model
        self.previous_context_model = None

ServedPretrainedModel.context_model = None


async def main():
    model = ServedPretrainedModel("http://localhost:8080", "gpt2")

    bos_token_id = (await model.tokenize("<BOS>"))[0]
    eos_token_id = (await model.tokenize("<EOS>"))[0]

    print([await model.detokenize([int(v) if not v.endswith(",") else int(v[:-1]) for v in sys.argv[1:]])])

if __name__ == "__main__":
    asyncio.run(main())
