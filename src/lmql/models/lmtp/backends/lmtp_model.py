import os
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class LMTPModelResult:
    sequences: np.ndarray
    scores: np.ndarray

class TokenStreamer:
    def __call__(self, input_ids: np.ndarray, scores: np.ndarray, **kwargs) -> bool:
        raise NotImplementedError

class LMTPModel:
    """
    Base interface for LMTP models.

    Implement at least the 'generate' method to enable sampling. To enable more advanced
    decoding strategies, implement the 'score' method as well.

    To register your model implementation, make sure to set an appropriate entry in 
    the LMTPModel.registry global dict:

        LMTPModel.registry["my-model"] = MyModelImplLMTPModel
    
    

    """
    max_batch_size: int = 1

    @property
    def eos_token_id(self):
        raise NotImplementedError

    @classmethod
    def load(self, model_name, **kwargs) -> 'LMTPModel':
        if ":" in model_name:
            backend_name = model_name.split(":")[0]
            if backend_name in LMTPModel.registry.keys():
                return LMTPModel.registry[backend_name](model_name, **kwargs)
        
        if not model_name in LMTPModel.registry.keys():
            if not "transformers" in LMTPModel.registry.keys():
                if "LMQL_BROWSER" in os.environ:
                    assert False, "The browser distribution of LMQL does not support HuggingFace Transformers models." + \
                        " Please use other model backends or install lmql locally with 'transformers' support (pip install lmql[hf])."
                else:
                    assert False, "Your distribution of LMQL does not support HuggingFace Transformers models." + \
                        " Please use other model backends or install lmql with the 'transformers' support (pip install lmql[hf])."
            return LMTPModel.registry["transformers"](model_name, **kwargs)
        return LMTPModel.registry[model_name](**kwargs)

    def __init__(self) -> None:
        pass
        # load the model

    def score(
        self,
        input_ids: np.ndarray,
        attention_mask: np.ndarray,
        **model_kwargs,
    )  -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes the log probabilities of a batch of input_ids (batch_size, seq_len),
        where input_ids are left-padded with 0 and attention is 0 for padding/masked tokens.

        If the model does not support scoring, return an array of 
        zeros of the same shape as input_ids (default behavior).
        """
        return np.zeros_like(input_ids)

    def generate(self,
        input_ids: np.ndarray,
        attention_mask: np.ndarray,
        temperature: float,
        max_new_tokens: int,
        bias_tensor: np.ndarray,
        streamer: TokenStreamer) -> LMTPModelResult:
        """
        Generates 'max_new_tokens' for each sequence in the batch of 'input_ids'.

        Before sampling from the next-token prediction of input_ids[i], additively applies
        'bias_tensor[i]', to enable masking.

        On each new produced token, invokes streamer(input_ids, np.ndarray, scores: List[np.ndarray]) 
        where input_ids is the batch of continued sequences of 'input_ids' and scores[-1] is the current
        token (logprob) distribution. 
        
        streamer() is not invoked for the last token, which is automatically streamed by the calling 
        code, extracting token and score from the returned LMTPModelResult.
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

    @staticmethod
    def register(name, module_dependencies = None):
        def wrapper(loader):
            import importlib
            if module_dependencies is not None:
                for module in module_dependencies:
                    try:
                        importlib.import_module(module)
                    except ImportError:
                        def error_func(*args, **kwargs):
                            assert False, "To use the {} backend, please install the '{}' package.".format(name, module)
                        LMTPModel.registry[name] = error_func
                        return
            loader() # the module will register itself in the registry
        return wrapper

LMTPModel.registry = {}