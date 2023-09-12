class LlamaCPPTokenizer:
    def __init__(self, model_identifier):
        from sentencepiece import SentencePieceProcessor
        self.model_identifier = model_identifier
        self.tokenizer = SentencePieceProcessor(model_identifier)

    @staticmethod
    def is_available(model_identifier):
        """
        Returns True if this tokenizer implementation is available for the given model identifier.
        """
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
        if asbytes:
            ids = self(s)["input_ids"]
            return self.decode_tokens_bytes(ids)
        else:
            return self.tokenizer.tokenize(s)

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