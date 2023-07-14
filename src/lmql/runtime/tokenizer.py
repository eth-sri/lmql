"""
Tokenizer interface required by LMQL. 

See .tokenizers for concrete implementations.
"""

import os
import pickle
import numpy as np
from typing import Optional

from lmql.runtime.caching import cache_file_exists, cachefile

from lmql.runtime.tokenizers.pure_python_tokenizer import PythonBackedTokenizer
from lmql.runtime.tokenizers.tiktoken_tokenizer import TiktokenTokenizer

global special_token_mappings
special_token_mappings = {}
global reverse_special_token_mappings
reverse_special_token_mappings = {}

class LMQLTokenizer:
    INVALID_CHARACTER = "\uFFFD"

    def __init__(self, model_identifier, tokenizer_impl=None, loader=None):
        self._tokenizer_impl = None
        self.loader_thread = None

        self.model_identifier = model_identifier

        self._vocab = None
        self.vocab_range = None

        if loader is not None:
            from threading import Thread
            def load():
                t = loader()
                self._tokenizer_impl = t
                self.loader_thread = None
                
                self._vocab = get_vocab(self.tokenizer_impl)
                self.vocab_range = max(max(self._vocab.values()) + 1, self.tokenizer_impl.vocab_size)
            self.loader_thread = Thread(target=load)
            self.loader_thread.start()
        else:
            self._tokenizer_impl = tokenizer_impl
            self._vocab = get_vocab(self.tokenizer_impl)
            self.vocab_range = max(max(self._vocab.values()) + 1, self.tokenizer_impl.vocab_size)

        if "FORCE_TIKTOKEN" in os.environ:
            assert type(self.tokenizer_impl) is TiktokenTokenizer

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
    def tokenizer_impl(self):
        if self._tokenizer_impl is None:
            self.loader_thread.join()
        return self._tokenizer_impl
    
    @property
    def name(self):
        return self.tokenizer_impl.name

    @property
    def vocab_size(self):
        """
        The vocab_size is the vocab_range (the highest vocabulary ID + 1)
        this allows us to use a dense one hot array where no IDs are skipped.
        """
        return self.vocab_range + 100 # 100 reserved tokens for LMQL tags

    @property
    def bos_token_id(self) -> Optional[int]:
        return self.tokenizer_impl.bos_token_id
    
    @property
    def eos_token_id(self):
        return self.tokenizer_impl.eos_token_id

    @property
    def vocab(self):
        return self.tokenizer_impl.vocab

    def convert_tokens_to_string(self, tokens):
        return self.tokenizer_impl.convert_tokens_to_string(tokens)

    def tokenize(self, s, asbytes=False):
        tokens = []
        for s in self.chunk_out_by_tags(s, tokenize=False):
            if s.startswith("lmql:"):
                if asbytes:
                    tokens.append(f"<{s}/>".encode("utf-8"))
                else:
                    tokens.append(s)
            else:
                tokens += self.tokenizer_impl.tokenize(s, asbytes=asbytes)

        return tokens
    
    def decode_bytes(self, input_ids):
        """
        Transforms a list of input ids into a byte sequences.
        """
        chunk = []
        result = []
        global reverse_special_token_mappings
        
        for i in input_ids:
            if i in reverse_special_token_mappings.keys():
                chunk_result = self.tokenizer_impl.decode_tokens_bytes(chunk)
                result += chunk_result
                result.append(("<" + reverse_special_token_mappings[i] + "/>").encode("utf-8"))
                chunk = []
            else:
                chunk.append(i)

        if len(chunk) > 0:
            result += self.tokenizer_impl.decode_tokens_bytes(chunk)

        return result

    def convert_bytes_to_ids(self, token_bytes):
        """
        Transforms text into a tokenized byte sequence.
        """
        # TODO: handle special IDs, i.e. tags (only relevant for tag use with LMTP backend)
        return self.tokenizer_impl.convert_token_bytes_to_ids(token_bytes)

    def convert_bytes_to_string(self, token_bytes):
        """
        Transforms token bytes into a text.
        """
        result = ""
        for chunk in self.chunk_out_by_special_ids_bytes(token_bytes):
            if type(chunk) is str:
                result += chunk
            else:
                result += self.tokenizer_impl.convert_bytes_to_string(chunk)
        return result

    def decode(self, input_ids):
        if len(input_ids) > 0 and type(input_ids[0]) is np.bytes_:
            return self.convert_bytes_to_string(input_ids)

        s = ""
        for chunk in self.chunk_out_by_special_ids(input_ids):
            if type(chunk) is str:
                s += chunk
            else:
                s += self.tokenizer_impl.decode(chunk, clean_up_tokenization_spaces=False)

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
    
    def chunk_out_by_special_ids_bytes(self, token_bytes, tokenize=True):
        global reverse_special_token_mappings
        global special_token_mappings
        c = []
        for i in token_bytes:
            try:
                decoded = i.decode("utf-8")
                
                if decoded.startswith("<") and decoded.endswith("/>") and decoded[1:-2] in special_token_mappings.keys():
                    if len(c) > 0:
                        yield c
                    c = []
                    yield decoded
                else:
                    c.append(i)
            except:
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
            

def load_tokenizer_notransformers(model_identifier):
    if not "SLOW_TOKENIZER_OK" in os.environ.keys():
        print("warning: using slow python-backed tokenizer as no other tokenizer is available for {} (transformers or tiktoken)".format(model_identifier))
    assert PythonBackedTokenizer.is_available(), "PythonBackedTokenizer not available. Please make sure the 'gpt3_tokenizer' package is installed."
    
    return PythonBackedTokenizer(model_identifier)

def load_tokenizer(model_identifier, type="auto", **kwargs):
    cache_identifier = model_identifier.replace("/", "-").replace(":", "__")
    cache_path = f"tokenizer-{cache_identifier}.pkl"

    if type in ["auto", "tiktoken"]:
        tiktoken_available = False
        # for GPT models we force non-HF tokenizers (tiktoken or python-backed)
        try:
            if TiktokenTokenizer.is_available(model_identifier):
                tiktoken_available = True
        except:
            tiktoken_available = False
        
        if tiktoken_available:
            def loader():
                if cache_file_exists(cache_path):
                    with cachefile(cache_path, "rb") as f:
                        return LMQLTokenizer(model_identifier, pickle.load(f))
                else:
                    t = TiktokenTokenizer(model_identifier)

                    with cachefile(cache_path, "wb") as f:
                        pickle.dump(t, f)
                return t
            
            return LMQLTokenizer(model_identifier, loader=loader)

    try:
        assert type in ["auto", "hf"]

        def loader():
            import os
            os.environ["TOKENIZERS_PARALLELISM"] = "true"

            from lmql.runtime.tokenizers.hf_tokenizer import TransformersTokenizer

            assert TransformersTokenizer.is_available(model_identifier), "TransformersTokenizer not available. Please make sure the 'transformers' package is installed."

            if cache_file_exists(cache_path):
                with cachefile(cache_path, "rb") as f:
                    return LMQLTokenizer(pickle.load(f), model_identifier)
            else:
                t = TransformersTokenizer.from_pretrained(model_identifier, **kwargs)

                with cachefile(cache_path, "wb") as f:
                    pickle.dump(t, f)
            return t
        return LMQLTokenizer(model_identifier, loader=loader)
    except Exception as e:
        # fallback to non-transformers tokenizer
        t = load_tokenizer_notransformers(model_identifier)

        return LMQLTokenizer(model_identifier, t)

def get_vocab(tokenizer):
    if hasattr(tokenizer, "vocab"):
        return tokenizer.vocab
    elif hasattr(tokenizer, "get_vocab"):
        return tokenizer.get_vocab()
    elif hasattr(tokenizer, "tokenizer_impl"):
        return get_vocab(tokenizer.tokenizer_impl)
    elif hasattr(tokenizer, "tokenizer"):
        return get_vocab(tokenizer.tokenizer)
    else:
        assert False, "Could not obtain full vocabulary from unknown tokenizer type: {}".format(type(tokenizer))

if __name__ == "__main__":
    import sys
    import torch

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
