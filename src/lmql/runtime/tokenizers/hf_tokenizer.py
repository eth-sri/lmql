def unicode(v):
    r = v.decode("utf-8", "ignore")
    assert type(r) is str
    return r

class TransformersTokenizer:
    def __init__(self, model_identifier, tokenizer):
        from transformers import AutoTokenizer
        self.model_identifier = model_identifier
        self.tokenizer = tokenizer

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

    @staticmethod
    def from_pretrained(model_identifier, **kwargs):
        from transformers import AutoTokenizer

        model_identifier = model_identifier
        tokenizer = AutoTokenizer.from_pretrained(model_identifier, **kwargs)

        if "LlamaTokenizer" in str(type(tokenizer)):
            return LlamaTransformersTokenizer(model_identifier, tokenizer)
        else:
            return TransformersTokenizer(model_identifier, tokenizer)

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

    def tokenize(self, text, asbytes=False, add_special_tokens=False):
        """
        Translates a string into a list of tokens (sub-strings)
        """
        if asbytes:
            ids = self(text, add_special_tokens=add_special_tokens)["input_ids"] 
            return self.decode_tokens_bytes(ids)
        return self.tokenizer.tokenize(text, add_special_tokens=add_special_tokens)

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

    def __call__(self, text, add_special_tokens=False):
        return self.tokenizer(text, add_special_tokens=add_special_tokens)

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
    
    def backend(self):
        return "transformers " + type(self.tokenizer).__name__
    
class LlamaTransformersTokenizer(TransformersTokenizer):
    """Aligns the behavior of HF LlamaTokenizer with that of gpt tokenizers."""

    space_token = "▁"
    nl_token = "<0x0A>"

    def convert_bytes_to_string(self, token_bytes):
        token_bytes = [str(self.tokenizer.bos_token_id).encode("utf-8")] + token_bytes
        s = super().convert_bytes_to_string(token_bytes)
        return s[len(self.tokenizer.bos_token):]
    
    def tokenize(self, text, asbytes=False, add_special_tokens=False):
        if not asbytes:
            if text == " " and LlamaTransformersTokenizer.space_token is not None:
                return [LlamaTransformersTokenizer.space_token]
            if text == "\n" and LlamaTransformersTokenizer.nl_token is not None:
                return [LlamaTransformersTokenizer.nl_token]
        return super().tokenize(text, asbytes, add_special_tokens)

    def __call__(self, text, add_special_tokens=False):
        prepend_dummy_tokens = ["@", "^", ""]
        # make sure that llama-specific INST tokens are tokenized as-is
        if text.startswith("[INST]"): prepend_dummy_tokens = [""]

        for dummy_token in prepend_dummy_tokens:
            text_to_tokenize = dummy_token + text
            
            text_to_tokenize = self.tokenizer.bos_token + text_to_tokenize
            result = super().__call__(text_to_tokenize, add_special_tokens=add_special_tokens)
            if len(result["input_ids"]) <= 2 and dummy_token != "":
                # "Tokenized text '{}' was merged with dummy token @ into '{}'".format(text_to_tokenize, [self.tokenizer.convert_ids_to_tokens(i) for i in result["input_ids"]])
                continue
            offset = 2 if len(dummy_token) > 0 else 1
            result["input_ids"] = result["input_ids"][offset:]
            return result

        assert False, "LLamaTransformersTokenizer.__call__ failed to workaround tokenization issue for '{}'".format(text)