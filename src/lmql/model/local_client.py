import torch
from transformers import AutoModelForCausalLM
import asyncio

class LocalClient:
    def __init__(self, model_identifier):
        self.model_identifier = model_identifier
        
        print("Using local in-process model", model_identifier)
        self.model = AutoModelForCausalLM.from_pretrained(model_identifier, device_map="auto")
        self.forward_queue = asyncio.Queue()
        self.forward_worker = asyncio.create_task(self.forward_worker_loop())
        print("Ready.")
    
    async def forward_worker_loop(self):
        while True:
            input_ids, attention_mask, fut = await self.forward_queue.get()
            
            res = self.model.forward(input_ids=input_ids, attention_mask=attention_mask)
            
            if input_ids.ndimension() == 2:
                next_token_logits = res.logits[:,-1]
            else:
                next_token_logits = res.logits[-1]
            
            fut.set_result({"next_token_logits": next_token_logits.detach()})
    
    def forward(self, input_ids, attention_mask):
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self.forward_queue.put_nowait((input_ids, attention_mask, fut))
        return fut
    
    def __del__(self):
        self.forward_worker.cancel()