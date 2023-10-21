from typing import Tuple
import sys
import torch
import numpy as np

from lmql.models.lmtp.backends.lmtp_model import (LMTPModel, LMTPModelResult,
                                                  TokenStreamer)
from lmql.models.lmtp.backends.transformers_model import TokenStreamerDisguisedAsStoppingCriterion, merge

class AwqModel(LMTPModel):
    def __init__(self, model_identifier, **kwargs):
        from awq import AutoAWQForCausalLM
        
        self.model_identifier = model_identifier
        self.kwargs = kwargs
        self.model_args = kwargs
        self.max_batch_size = kwargs.pop("batch_size", 16)
        self.device = kwargs.pop("device", "cuda")

        print("[Loading awq model from", self.model_identifier, " with ", kwargs, "]", flush=True)
        
        self.model = AutoAWQForCausalLM.from_quantized(self.model_identifier[len("awq:"):], fuse_layers=False, safetensors=True, batch_size=self.max_batch_size,  **self.model_args)


    def model_info(self):
        import awq
        return {
            "model_identifier": self.model_identifier[len("awq:"):],
            "model_type": "awq",
            "constructor": "AutoAWQForCausalLM(model_path='{}'{})".format(self.model_identifier[len("awq:"):], ", " + ", ".join(["{}={}".format(k, v) for k,v in self.kwargs.items()]) if len(self.kwargs) > 0 else ""),
            "awq": awq.__version__,
        }

    @property
    def eos_token_id(self):
        return self.model.model.config.eos_token_id

    def score(self, input_ids: torch.LongTensor, attention_mask: torch.LongTensor, **model_kwargs) -> Tuple[torch.FloatTensor, torch.FloatTensor]:
        input_ids = torch.tensor(input_ids).to(self.device)
        attention_mask = torch.tensor(attention_mask).to(self.device)
        
        # prepare model inputs
        model_inputs = self.model.model.prepare_inputs_for_generation(input_ids, **model_kwargs, attention_mask=attention_mask, eos_token_id=self.eos_token_id)
        model_inputs["attention_mask"] = attention_mask

        token_scores = []
        
        outputs = self.model(
            **model_inputs,
            return_dict=True,
            output_attentions=False,
            output_hidden_states=False,
        )

        next_token_logits = outputs.logits[:, :-1, :]
        next_token_logits = torch.log_softmax(next_token_logits, dim=-1)
        token_scores = next_token_logits.gather(-1, input_ids[:,1:].unsqueeze(-1))

        return np.array([[0.0] + scores.flatten().tolist() for scores in token_scores])
    
    def generate(self, input_ids: torch.LongTensor, attention_mask: torch.LongTensor, 
                 temperature: float, max_new_tokens: int, 
                 bias_tensor: torch.FloatTensor, streamer: TokenStreamer, **kwargs) -> LMTPModelResult:
        input_ids = torch.tensor(input_ids).to(self.device)
        attention_mask = torch.tensor(attention_mask).to(self.device)
        
        generate_args = {
            "input_ids": input_ids,
            "do_sample": temperature > 0.0,
            "attention_mask": attention_mask,
            **({"temperature": temperature} if temperature > 0.0 else {}),
            "max_new_tokens": max_new_tokens,
            "logits_processor": self.logits_processors(bias_tensor),
            "output_scores": True,
            "return_dict_in_generate": True
        }

        # factor in optional user-provided kwargs
        merge(generate_args, kwargs, prioritize="left")

        result = self.model.generate(**generate_args, stopping_criteria=[TokenStreamerDisguisedAsStoppingCriterion(streamer)], 
                                     eos_token_id=self.eos_token_id, pad_token_id=self.eos_token_id)
        return LMTPModelResult(sequences=result.sequences, scores=result.scores)

    def logits_processors(self, logit_biases):
        bias_tensors = None
        make_bias_tensor = self.make_bias_tensor
        
        if len(logit_biases) == 0:
            return []

        class BatchLogitsProcessor:
            def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
                nonlocal bias_tensors

                if bias_tensors is None:
                    bias_tensors = torch.tensor(make_bias_tensor(logit_biases, scores.shape[-1])).to(scores.device)

                return torch.log_softmax(scores + bias_tensors, dim=-1)

        return [BatchLogitsProcessor()]

LMTPModel.registry["awq"] = AwqModel
