import sys
import numpy as np

from lmql.models.lmtp.backends import LMTPModel
from lmql.models.lmtp.lmtp_scheduler import TokenStreamer
from lmql.runtime.tokenizer import load_tokenizer

import transformers

# simple 'main' for testing backends
if __name__ == "__main__":
    backend = sys.argv[1]
    model: LMTPModel = LMTPModel.load(backend)
    t = load_tokenizer("huggyllama/llama-7b")

    s = sys.argv[2]
    input_ids = [t.bos_token_id] + t(s)["input_ids"]

    class DebugStreamer:
        def __call__(self, tokens, scores):
            print(t.decode(tokens))
            return False

    model.generate(np.array(input_ids), np.ones_like(input_ids), 1.0, 10, None, DebugStreamer())