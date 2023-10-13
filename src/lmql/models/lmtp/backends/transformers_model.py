from typing import Tuple
import torch
from lmql.models.lmtp.backends.lmtp_model import LMTPModel, LMTPModelResult, TokenStreamer
import numpy as np

def format_call(model_name, **kwargs):
    if len(kwargs) == 0:
        return f'"{model_name}"'
    return f'"{model_name}", {", ".join([f"{k}={v}" for k, v in kwargs.items()])}'

def merge(kwargs1, kwargs2, prioritize="left"):
    for k, v in kwargs2.items():
        if k in kwargs1:
            if prioritize == "left":
                continue
            else: # right
                kwargs1[k] = v
        else:
            kwargs1[k] = v
    return kwargs1

# store version info about e.g. 'transformers' package
version_info = {}

class TransformersLLM(LMTPModel):
    def __init__(self, model_identifier, **kwargs):
        self.model_identifier = model_identifier
        self.model_args = kwargs
        self.loader = kwargs.pop("loader", "transformers")

        self.max_batch_size = kwargs.pop("batch_size", 32)

        self.silent = kwargs.pop("silent", False)

        if not self.silent:
            print("[Loading", self.model_identifier, "with", self.model_constructor() + "]", flush=True)

        if self.loader == "auto-gptq":
            from auto_gptq import AutoGPTQForCausalLM
            self.model = AutoGPTQForCausalLM.from_quantized(self.model_identifier, **self.model_args)
        else:
            from transformers import AutoModelForCausalLM            
            self.model = AutoModelForCausalLM.from_pretrained(self.model_identifier, **self.model_args)
        
        if not self.silent:
            print("[", self.model_identifier, " ready on device ", self.model.device, 
        flush=True, sep="", end="]\n")

    @property
    def eos_token_id(self):
        return self.model.config.eos_token_id

    def score(self, input_ids: torch.LongTensor, attention_mask: torch.LongTensor, **model_kwargs) -> Tuple[torch.FloatTensor, torch.FloatTensor]:
        input_ids = torch.tensor(input_ids).to(self.model.device)
        attention_mask = torch.tensor(attention_mask).to(self.model.device)
        
        # prepare model inputs
        model_inputs = self.model.prepare_inputs_for_generation(input_ids, **model_kwargs, attention_mask=attention_mask, eos_token_id=self.eos_token_id)
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
        input_ids = torch.tensor(input_ids).to(self.model.device)
        attention_mask = torch.tensor(attention_mask).to(self.model.device)
        
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

    def model_constructor(self):
        if self.loader == "auto-gptq":
            return "AutoGPTQForCausalLM.from_quantized({})".format(format_call(self.model_identifier, **self.model_args))
        else:
            return "AutoModelForCausalLM.from_pretrained({})]".format(format_call(self.model_identifier, **self.model_args))

    def version_info(self):
        global version_info
        
        if len(version_info) == 0:
            if self.loader == "auto-gptq":
                import auto_gptq
                version_info = {
                    "auto_gptq": auto_gptq.__version__
                }
            else:
                import transformers
                version_info = {
                    "transformers": transformers.__version__
                }

                # try to get version for bitsandbytes
                try:
                    # check if bitsandbytes is installed
                    import bitsandbytes
                    # use pip to get version (doesn not have __version__ attribute)
                    import subprocess
                    result = subprocess.run(["pip", "show", "bitsandbytes"], capture_output=True)
                    print(result)
                    if result.returncode == 0:
                        version_info["bitsandbytes"] = result.stdout.decode("utf-8").split("\n")[1].split(":")[1].strip()
                except:
                    pass
        return version_info

    def model_info(self):
        return {
            "model": self.model_identifier,
            "model_type": self.loader,
            # use single quotes to avoid issues with JSON
            "constructor": self.model_constructor().replace('"', "'"),
            **self.version_info()
        }

class TokenStreamerDisguisedAsStoppingCriterion:
    def __init__(self, token_streamer: TokenStreamer):
        self.token_streamer = token_streamer

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        self.token_streamer(input_ids, scores, **kwargs)
        return False

LMTPModel.registry["transformers"] = TransformersLLM
