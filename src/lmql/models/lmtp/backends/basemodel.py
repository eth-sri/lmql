import os
import torch
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class LMTPModelResult:
    sequences: torch.LongTensor
    scores: torch.FloatTensor

class TokenStreamer:
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        raise NotImplementedError

class LMTPModel:
    max_batch_size: int = 1

    @property
    def device(self):
        return torch.device("cpu")

    @property
    def eos_token_id(self):
        raise NotImplementedError

    @classmethod
    def load(self, model_name, **kwargs):
        if not model_name in LMTPModel.registry.keys():
            if not "transformers" in LMTPModel.registry.keys():
                if "LMQL_BROWSER" in os.environ:
                    assert False, "The browser distribution of LMQL does not support HuggingFace Transformers models.\
                        Please use openai/ models or install lmql with 'transformers' support (pip install lmql[hf])."
                else:
                    assert False, "Your distribution of LMQL does not support HuggingFace Transformers models.\
                        Please use openai/ models or install lmql with 'transformers' support (pip install lmql[hf])."
            return LMTPModel.registry["transformers"](model_name, **kwargs)
        return LMTPModel.registry[model_name](**kwargs)

    def __init__(self) -> None:
        pass
        # load the model

    def score(
        self,
        input_ids: torch.LongTensor,
        attention_mask: torch.LongTensor,
        **model_kwargs,
    )  -> Tuple[torch.FloatTensor, torch.FloatTensor]:
        """
        Computes the log probabilities of a batch of input_ids (batch_size, seq_len),
        where input_ids are left-padded with 0 and attention is 0 for padding/masked tokens.

        If the model does not support scoring, return an array of 
        zeros of the same shape as input_ids (default behavior).
        """
        return np.zeros_like(input_ids)

    def generate(self,
        input_ids: torch.LongTensor,
        attention_mask: torch.LongTensor,
        temperature: float,
        max_new_tokens: int,
        bias_tensor: torch.FloatTensor,
        streamer: TokenStreamer) -> LMTPModelResult:
        """
        Generates 'max_new_tokens' for each sequence in the batch of 'input_ids'.

        Before sampling from the next-token prediction of input_ids[i], additively applies
        'bias_tensor[i]', to enable masking.

        On each new produced token, invokes streamer(input_ids, torch.LongTensor, scores: List[torch.FloatTensor]) 
        where input_ids is the batch of continued sequences of 'input_ids' and scores[-1] is the current
        token (logprob) distribution.
        """
        pass

    def make_bias_tensor(self, logit_biases, vocab_size):
        bias_tensors = [np.zeros(vocab_size) for _ in logit_biases]
        for i, bias in enumerate(logit_biases):
            if len(bias) > 0:
                indices = np.array(list(bias.keys()), dtype=np.int64)
                values = np.array(list(bias.values()), dtype=np.float32)
                bias_tensors[i][indices] = values
        return np.stack(bias_tensors)

LMTPModel.registry = {}