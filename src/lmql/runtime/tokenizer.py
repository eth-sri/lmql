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
         
        def decode(self, input_ids):
            # set typed array type of input_ids to int
            return str(js.detokenize_gpt(to_js([int(i) for i in input_ids])))

        def __call__(self, s: str):
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


def load_tokenizer(model_identifier):
    import os

    # check environment of USE_JS_TOKENIZER
    if "LMQL_BROWSER" in os.environ:
        return get_js_tokenizer(model_identifier)

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
            return pickle.load(f)
    else:
        from transformers import AutoTokenizer
        t = AutoTokenizer.from_pretrained(model_identifier)
        with open(cache_path, "wb") as f:
            pickle.dump(t, f)
        return t

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