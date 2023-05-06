import asyncio

def get_js_tokenizer(model_identifier):
    import js
    from pyodide.ffi import to_js

    assert "gpt" in model_identifier, "JS tokenizer only supports GPT models."

    class JSBridgedTokenizer:
        """ Custom tokenizer to be used only in a browser environment. This tokenizer only supports GPT tokenization. """
        def __init__(self):
            self.bos_token_id = 50256
            self.eos_token_id = 50256
            self._vocab = None

        @property
        def vocab_size(self):
            return len(self.vocab)

        @property
        def vocab(self):
            if self._vocab is None:
                self._vocab = js.get_vocab().to_py()
            return self._vocab

        def convert_tokens_to_string(self, tokens):
            return js.convert_tokens_to_string_gpt(to_js(tokens))

        def tokenize(self, s):
            unpack = False
            if type(s) is not list:
                s = [s]
                unpack = True
            tokens = [js.tokenize_gpt_toks(se).to_py() for se in s]
            
            if unpack:
                return tokens[0]
            else:
                return tokens
         
        def decode(self, input_ids, clean_up_tokenization_spaces=None):
            # set typed array type of input_ids to int
            return str(js.detokenize_gpt(to_js([int(i) for i in input_ids])))

        def __call__(self, s: str, add_special_tokens=False):
            unpack = False
            if type(s) is not list:
                s = [s]
                unpack = True
            input_ids = [[int(v) for v in js.tokenize_gpt(se)] for se in s]
            
            if unpack:
                return {"input_ids": input_ids[0]}
            else:
                return {"input_ids": input_ids}
    
    return JSBridgedTokenizer()

global special_token_mappings
special_token_mappings = {}
global reverse_special_token_mappings
reverse_special_token_mappings = {}

class LMQLTokenizer:
    INVALID_CHARACTER = "\uFFFD"

    def __init__(self, tokenizer_impl, model_identifier):
        self.tokenizer_impl = tokenizer_impl
        self.model_identifier = model_identifier
        self.detokenizer_cache = {}

        self._vocab = get_vocab(self.tokenizer_impl)
        self.vocab_range = max(self._vocab.values()) + 1

    @property
    def model_vocab_size(self):
        """
        The model vocab size is the size of the vocabulary that a model uses
        as the dimensionality of its output distribution. This is different from
        the vocab_size of the tokenizer, which is the size of the vocabulary
        + some reserved LMQL-specific tokens.
        """
        return self.vocab_range

    @property
    def vocab_size(self):
        """
        The vocab_size is the vocab_range (the highest vocabulary ID + 1)
        this allows us to use a dense one hot array where no IDs are skipped.
        """
        return self.vocab_range + 100 # 100 reserved tokens for LMQL tags

    @property
    def bos_token_id(self):
        return self.tokenizer_impl.bos_token_id
    
    @property
    def eos_token_id(self):
        return self.tokenizer_impl.eos_token_id

    @property
    def vocab(self):
        return self.tokenizer_impl.vocab

    def convert_tokens_to_string(self, tokens):
        return self.tokenizer_impl.convert_tokens_to_string(tokens)

    def tokenize(self, s):
        tokens = []
        for s in self.chunk_out_by_tags(s, tokenize=False):
            if s.startswith("lmql:"):
                tokens.append(s)
            else:
                tokens += self.tokenizer_impl.tokenize(s)
        return tokens
        
    def decode(self, input_ids):
        key = str(input_ids)
        n = len(input_ids)
        if n in self.detokenizer_cache.keys():
            if key in self.detokenizer_cache[n].keys():
                return self.detokenizer_cache[n][key]
        if n-1 in self.detokenizer_cache.keys():
            key = str(input_ids[:-1])
            if key in self.detokenizer_cache[n-1].keys():
                global reverse_special_token_mappings
                # print("secondary cache hit")
                if input_ids[-1] >= self.model_vocab_size:
                    extended = self.detokenizer_cache[n-1][key] + "<" + reverse_special_token_mappings[input_ids[-1]] + "/>"
                else:
                    extended = self.detokenizer_cache[n-1][key] + self.tokenizer_impl.decode([input_ids[-1]], clean_up_tokenization_spaces=False)
                    if self.INVALID_CHARACTER in extended:
                        return self.detokenizer_cache[n-1][key]
                if not n in self.detokenizer_cache.keys():
                    self.detokenizer_cache[n] = {}
                self.detokenizer_cache[n][str(input_ids)] = extended
                return extended

        s = ""
        for chunk in self.chunk_out_by_special_ids(input_ids):
            if type(chunk) is str:
                s += chunk
            else:
                s += self.tokenizer_impl.decode(chunk, clean_up_tokenization_spaces=False)

        if not n in self.detokenizer_cache.keys():
            self.detokenizer_cache[n] = {}
        self.detokenizer_cache[n][key] = s

        return s

    def __call__(self, s: str, add_special_tokens=False):
        input_ids = []
        unpack = False
        if type(s) is not list:
            s = [s]
            unpack = True
        
        for seq in s:
            chunk_input_ids = []
            for chunk in self.chunk_out_by_tags(seq):
                if type(chunk) is int:
                    chunk_input_ids.append(chunk)
                else:
                    result = self.tokenizer_impl(chunk, add_special_tokens=add_special_tokens)["input_ids"]
                    chunk_input_ids += result
            input_ids.append(chunk_input_ids)
        
        if unpack:
            return {"input_ids": input_ids[0]}
        else:
            return {"input_ids": input_ids}
    
    def is_special_id(self, id: str):
        return id >= self.model_vocab_size

    def truncate_to_model_dim(self, mask):
        if mask is None:
            return mask
        return mask[:self.model_vocab_size]

    def special_token_id(self, identifier):
        global special_token_mappings
        global reverse_special_token_mappings
        
        if identifier not in special_token_mappings:
            if len(special_token_mappings) == 0:
                # offset vocabulary IDs by at least 1 to avoid collisions with the tokenizer's vocabulary
                offset = self.vocab_range + 1
                special_token_mappings[identifier] = offset
                reverse_special_token_mappings[offset] = identifier
            else:
                next_id = max(special_token_mappings.values()) + 1
                special_token_mappings[identifier] = next_id
                reverse_special_token_mappings[next_id] = identifier
                assert next_id < self.vocab_size, "LMQL special tokens exhausted (only 100 allowed by default)"
        return special_token_mappings[identifier]
    
    def chunk_out_by_special_ids(self, input_ids, tokenize=True):
        global reverse_special_token_mappings
        c = []
        for i in input_ids:
            if i in reverse_special_token_mappings.keys():
                if len(c) > 0:
                    yield c
                c = []
                yield "<" + reverse_special_token_mappings[i] + "/>"
            else:
                c.append(i)
        yield c
    
    def chunk_out_by_tags(self, s, tokenize=True):
        # filter out all special tokens <lmql:.../>
        import re
        segments = []
        offset = 0
        for m in re.finditer(r"<lmql:(.*?)\/>", s):
            segments.append(s[offset:m.start()])
            if tokenize:
                segments.append(self.special_token_id("lmql:" + m.group(1)))
            else:
                segments.append("lmql:" + m.group(1))
            offset = m.end()
        segments.append(s[offset:])
        return segments

def load_tokenizer(model_identifier):
    import os

    # check environment of USE_JS_TOKENIZER
    if "LMQL_BROWSER" in os.environ:
        return LMQLTokenizer(get_js_tokenizer(model_identifier), model_identifier)

    from transformers import AutoTokenizer
    import torch

    # first try to load pickled tokenizer from cache (faster)
    import pickle
    import pathlib

    cache_dir = pathlib.Path.home() / ".cache" / "lmql"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_identifier = model_identifier.replace("/", "-")
    cache_path = cache_dir / f"tokenizer-{cache_identifier}.pkl"

    if cache_path.exists():
        with open(cache_path, "rb") as f:
            return LMQLTokenizer(pickle.load(f), model_identifier)
    else:
        from transformers import AutoTokenizer
        t = AutoTokenizer.from_pretrained(model_identifier)
        with open(cache_path, "wb") as f:
            pickle.dump(t, f)
        return LMQLTokenizer(t, model_identifier)

def get_vocab(tokenizer):
    if hasattr(tokenizer, "vocab"):
        return tokenizer.vocab
    elif hasattr(tokenizer, "get_vocab"):
        return tokenizer.get_vocab()
    elif hasattr(tokenizer, "tokenizer_impl"):
        return get_vocab(tokenizer.tokenizer_impl)
    else:
        assert False, "Could not obtain full vocabulary from unknown tokenizer type: {}".format(type(tokenizer))

if __name__ == "__main__":
    import sys

    model_identifier = sys.argv[1]
    t = load_tokenizer(model_identifier)

    to_tokenize = sys.argv[2]

    if to_tokenize.startswith("["):
        import json
        to_tokenize = json.loads(to_tokenize)
        print(str([t.decode(torch.tensor(to_tokenize))])[1:-1])
    else:
        res = t(to_tokenize)
        print(res)
        print(t.convert_ids_to_tokens(res["input_ids"]))
        n = 0
        result = ""
        for t,id in sorted(t.vocab.items(), key=lambda p: p[1]):
            # contains digit
            digits = "0123456789"
            if len(t) < 4 and any(c in digits for c in t):
                print(t,id)
                n += 1
                result += f""""{t}","""
        print(n)
        print(result)
