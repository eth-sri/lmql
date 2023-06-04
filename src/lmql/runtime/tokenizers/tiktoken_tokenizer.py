import os
from lmql.runtime.stats import Stats

def unicode(v):
    r = v.decode("utf-8", "ignore")
    assert type(r) is str
    return r

class TiktokenTokenizer:
    def __init__(self, model_identifier):
        import tiktoken

        self.model_identifier = model_identifier
        self.enc = tiktoken.encoding_for_model(model_identifier)

        self.bytes_can_concat = True

        self.vocab = {self.enc.decode([i]): i for i in range(self.enc.max_token_value)}
        self.stats = Stats("tiktoken")

        for i in range(self.enc.n_vocab, self.enc.max_token_value):
            token_name = f"<|special_{i}|>"
            assert token_name not in self.vocab, f"token {token_name} already in vocab"
            self.vocab[token_name] = i

    @staticmethod
    def is_available(model_identifier):
        try:
            import tiktoken
            tiktoken.encoding_for_model(model_identifier)
        except ImportError:
            return False
        except KeyError:
            return False
        return True

    # do not picke self.enc
    def __getstate__(self):
        return {
            "model_identifier": self.model_identifier,
            "vocab": self.vocab
        }
    
    def __setstate__(self, state):
        import tiktoken
        
        self.model_identifier = state["model_identifier"]
        self.vocab = state["vocab"]
        self.enc = tiktoken.encoding_for_model(self.model_identifier)
        self.stats = Stats("tiktoken")

    def encode(self, text):
        return self.enc.encode(text, allowed_special={"<|endoftext|>"})

    def tokenize(self, text, asbytes=False):
        ids = self.encode(text)
        tokens = self.enc.decode_tokens_bytes(ids)
        
        if asbytes:
            return tokens
        return [t.decode("raw-unicode-escape", "backslashreplace") for t in tokens]

    def decode_tokens_bytes(self, ids):
        return self.enc.decode_tokens_bytes(ids)

    def decode(self, ids, clean_up_tokenization_spaces=True):
        return self.enc.decode(ids)
    
    def convert_bytes_to_string(self, token_bytes):
        return b"".join(token_bytes).decode("utf-8", "replace")
    
    def convert_token_bytes_to_ids(self, tokens):
        text = self.convert_bytes_to_string(tokens)
        return self.encode(text)

    def __call__(self, text_or_list, add_special_tokens=False):
        if isinstance(text_or_list, str):
            input_ids = self.encode(text_or_list)
        else:
            input_ids = [self.encode(text) for text in text_or_list]

        return {"input_ids": input_ids}

    @property
    def vocab_size(self):
        return self.enc.max_token_value + 1
    
    @property
    def eos_token_id(self):
        return self.enc.eot_token

    @property
    def bos_token_id(self):
        return self.enc.eot_token

    def convert_tokens_to_string(self, tokens):
        return "".join(tokens)

    @property
    def name(self):
        return "tiktoken-" + self.model_identifier

def get_tokenizer(model_identifier):
    import tiktoken

    if model_identifier.startswith("openai/"):
        model_identifier = model_identifier[len("openai/"):]
    
    return TiktokenTokenizer(model_identifier)