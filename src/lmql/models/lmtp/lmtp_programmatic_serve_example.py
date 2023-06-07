"""
Using the 'serve' function as shown below, you can
run your own LMTP HuggingFace model server.

Parameters beyond server configuration are directly passed on to the
AutoModel.from_pretrained function.
"""

import lmql
import torch

lmql.serve("gpt2", port=9999, cuda=True, resume_download=True)