
"""



class LlamaCPPTokenizer:
    def __init__(self, model_identifier):
        from transformers import LlamaTokenizer
        self.model_identifier = model_identifier
        self.tokenizer = LlamaTokenizer(model_identifier)

    @staticmethod
    def is_available(model_identifier):
        # Returns True if this tokenizer implementation is available for the given model identifier.
        try:
            from transformers import LlamaTokenizer
            return True
        except ImportError:
            return False
    
    def __getstate__(self):
        return {
            "model_identifier": self.model_identifier,
            "tokenizer": self.tokenizer
        }
    
    def __setstate__(self, state):
        self.model_identifier = state["model_identifier"]
        self.tokenizer = state["tokenizer"]
    
    def tokenize(self, s, asbytes=False):
        if s == " " or s == "\n":
            return "_" if s==" " else "<0x0A>"
        print("SSSss ", s)
        print(asbytes)
        if asbytes:
            ids = self(s)["input_ids"]
            return self.decode_tokens_bytes(ids)
        else:
            r = self.tokenizer.tokenize(s)
            print("ASDA", r)
            return r

    @property
    def vocab(self):
        return self.tokenizer.vocab

    @property
    def vocab_size(self):
        return self.tokenizer.vocab_size

    @property
    def eos_token_id(self):
        return self.tokenizer.eos_token_id()

    @property
    def bos_token_id(self):
        return self.tokenizer.bos_token_id()
    
    @property
    def name(self):
        return "llama.cpp-" + self.model_identifier
    

"""
class LlamaCPPTokenizer:
    def __init__(self, model_identifier):
        from sentencepiece import SentencePieceProcessor
        self.model_identifier = model_identifier
        self.tokenizer = SentencePieceProcessor(model_identifier)

    @staticmethod
    def is_available(model_identifier):
        # Returns True if this tokenizer implementation is available for the given model identifier.
        try:
            from sentencepiece import SentencePieceProcessor
            return True
        except ImportError:
            return False
    
    def __getstate__(self):
        return {
            "model_identifier": self.model_identifier,
            "tokenizer": self.tokenizer
        }
    
    def __setstate__(self, state):
        from sentencepiece import SentencePieceProcessor
        
        self.model_identifier = state["model_identifier"]
        self.tokenizer = state["tokenizer"]
    
    def tokenize(self, s, asbytes=False):
        print("SSSss ", s)
        print(asbytes)

        if s == " " or s == "\n":
            return ["_"] if s==" " else ["<0x0A>"]
        if asbytes:
            ids = self(s)["input_ids"]
            return self.decode_tokens_bytes(ids)
        else:
            return self.tokenizer.tokenize(s)
        
    def decode_tokens_bytes(self, ids):
        """
        Converts a list of token ids into a list of token bytes.
        """
        # translate 'ids' into a bytes representation
        return [f"{i}".encode("utf-8") for i in ids]

    def __call__(self, text, add_special_tokens=False):
        # text_to_tokenize = "<s>" + text_to_tokenize
        result =  self.tokenizer.encode(text)
        return {
            "input_ids": result
        }
    
    def convert_bytes_to_string(self, token_bytes):
        """
        Converts a list of token bytes into a string.

        It must hold that self.convert_bytes_to_string(self.decode_tokens_bytes(ids)) == self.decode(ids).
        """
        ids = self.convert_token_bytes_to_ids(token_bytes)
        res = self.tokenizer.decode(ids)
        print("Input tokens", token_bytes)
        print("Output res", res)
        return res
    
    def decode(self, ids, clean_up_tokenization_spaces=True):
        """
        Converts a list of token ids into a string.
        """
        return self.tokenizer.decode(ids)
    
    def convert_token_bytes_to_ids(self, tokens):
        """
        Converts a list of token bytes into a list of token ids.

        Inverse of self.decode_tokens_bytes.
        """
        return [int(t.decode("utf-8")) for t in tokens]

    @property
    def vocab(self):
        return { self.tokenizer.id_to_piece(id): id for id in range(self.tokenizer.get_piece_size()) }

    @property
    def vocab_size(self):
        return self.tokenizer.vocab_size()

    @property
    def eos_token_id(self):
        return self.tokenizer.eos_id()

    @property
    def bos_token_id(self):
        return self.tokenizer.bos_id()
    
    @property
    def name(self):
        return "llama.cpp-" + self.model_identifier
