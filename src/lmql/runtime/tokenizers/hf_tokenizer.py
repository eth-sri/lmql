import os
from lmql.runtime.stats import Stats

def unicode(v):
    r = v.decode("utf-8", "ignore")
    assert type(r) is str
    return r

class TransformersTokenizer:
    def __init__(self, model_identifier):
        from transformers import AutoTokenizer
        
        self.model_identifier = model_identifier
        self.tokenizer = AutoTokenizer.from_pretrained(model_identifier)

    @staticmethod
    def is_available(model_identifier):
        """
        Returns True if this tokenizer implementation is available for the given model identifier.
        """
        try:
            from transformers import AutoTokenizer
        except ImportError:
            return False
        return True

    # do not picke self.enc
    def __getstate__(self):
        return {
            "model_identifier": self.model_identifier,
            "tokenizer": self.tokenizer
        }
    
    def __setstate__(self, state):
        from transformers import AutoTokenizer
        
        self.model_identifier = state["model_identifier"]
        self.tokenizer = state["tokenizer"]

    def tokenize(self, text, asbytes=False):
        """
        Translates a string into a list of tokens (sub-strings)
        """
        if asbytes:
            return self.decode_tokens_bytes(self.tokenizer(text)["input_ids"])
        return self.tokenizer.tokenize(text)

    def decode_tokens_bytes(self, ids):
        """
        Converts a list of token ids into a list of token bytes.
        """
        # translate 'ids' into a bytes representation
        return [f"{i}".encode("utf-8") for i in ids]

    def decode(self, ids, clean_up_tokenization_spaces=True):
        """
        Converts a list of token ids into a string.
        """
        return self.tokenizer.decode(ids, clean_up_tokenization_spaces=clean_up_tokenization_spaces)
    
    def convert_bytes_to_string(self, token_bytes):
        """
        Converts a list of token bytes into a string.

        It must hold that self.convert_bytes_to_string(self.decode_tokens_bytes(ids)) == self.decode(ids).
        """
        ids = self.convert_token_bytes_to_ids(token_bytes)
        return self.tokenizer.decode(ids)
    
    def convert_token_bytes_to_ids(self, tokens):
        """
        Converts a list of token bytes into a list of token ids.

        Inverse of self.decode_tokens_bytes.
        """
        return [int(t.decode("utf-8")) for t in tokens]

    def __call__(self, text_or_list, add_special_tokens=False):
        return self.tokenizer(text_or_list, add_special_tokens=add_special_tokens)

    @property
    def vocab_size(self):
        return self.tokenizer.vocab_size
    
    @property
    def eos_token_id(self):
        return self.tokenizer.eos_token_id

    @property
    def bos_token_id(self):
        return self.tokenizer.bos_token_id

    def convert_tokens_to_string(self, tokens):
        return self.tokenizer.convert_tokens_to_string(tokens)

    @property
    def name(self):
        return "hf-" + self.model_identifier