import lmql
import torch

lmql.serve("gpt2", port=9999, cuda=True, resume_download=True)