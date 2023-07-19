from typing import Tuple
import torch
from lmql.models.lmtp.backends.lmtp_model import LMTPModel, LMTPModelResult, TokenStreamer
import random

class TransformersLLM(LMTPModel):
    def __init__(self, model_identifier, **kwargs):
        self.model_identifier = model_identifier
        self.model_args = kwargs

        if self.model_args.pop("loader", None) == "auto-gptq":
            from auto_gptq import AutoGPTQForCausalLM
            print("[Loading", self.model_identifier, "with", f"AutoGPTQForCausalLM.from_quantized({self.model_identifier}, {str(self.model_args)[1:-1]})]", flush=True)
            self.model = AutoGPTQForCausalLM.from_quantized(self.model_identifier, **self.model_args)
        else:
            from transformers import AutoModelForCausalLM
            print("[Loading", self.model_identifier, "with", f"AutoModelForCausalLM.from_pretrained({self.model_identifier}, {str(self.model_args)[1:-1]})]", flush=True)
            self.model = AutoModelForCausalLM.from_pretrained(self.model_identifier, **self.model_args)
        
        print("[", self.model_identifier, " ready on device ", self.model.device, 
        flush=True, sep="", end="]\n")

        self.max_batch_size = kwargs.get("batch_size", 8)

    @property
    def eos_token_id(self):
        return self.model.config.eos_token_id

    def score(self, input_ids: torch.LongTensor, attention_mask: torch.LongTensor, **model_kwargs) -> Tuple[torch.FloatTensor, torch.FloatTensor]:
        input_ids = torch.tensor(input_ids)
        attention_mask = torch.tensor(attention_mask)
        
        # prepare model inputs
        model_inputs = self.model.prepare_inputs_for_generation(input_ids, **model_kwargs, eos_token_id=self.eos_token_id)
        model_inputs["attention_mask"] = attention_mask

        token_scores = []
        
        outputs = self.model(
            **model_inputs,
            return_dict=True,
            output_attentions=False,
            output_hidden_states=False,
        )

        next_token_logits = outputs.logits[:, -len(input_ids), :]
        next_token_logits = torch.log_softmax(next_token_logits, dim=-1)
        token_scores = next_token_logits.gather(-1, input_ids)

        return token_scores
    
    def generate(self, input_ids: torch.LongTensor, attention_mask: torch.LongTensor, 
                 temperature: float, max_new_tokens: int, 
                 bias_tensor: torch.FloatTensor, streamer: TokenStreamer) -> LMTPModelResult:
        input_ids = torch.tensor(input_ids)
        attention_mask = torch.tensor(attention_mask)
        
        kwargs = {
            "input_ids": input_ids.to(self.model.device),
            "do_sample": temperature > 0.0,
            "attention_mask": attention_mask.to(self.model.device),
            "temperature": temperature,
            "max_new_tokens": max_new_tokens,
            "logits_processor": self.logits_processors(bias_tensor),
            "output_scores": True,
            "return_dict_in_generate": True
        }

        result = self.model.generate(**kwargs, stopping_criteria=[TokenStreamerDisguisedAsStoppingCriterion(streamer)], 
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

                return scores + bias_tensors

        return [BatchLogitsProcessor()]

class TokenStreamerDisguisedAsStoppingCriterion:
    def __init__(self, token_streamer: TokenStreamer):
        self.token_streamer = token_streamer

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        self.token_streamer(input_ids, scores, **kwargs)
        return False

LMTPModel.registry["transformers"] = TransformersLLM