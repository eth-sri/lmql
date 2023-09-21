"""
Implements lmql.score and context.score as accessible 
from within LMQL queries.
"""
from typing import List
import numpy as np
import lmql.runtime.dclib as dc
import lmql.utils.nputil as nputil

class ScoringResult:
    def __init__(self, prompt, continuations, seqs: List[dc.seq]):
        self.seqs = [s.expand() for s in seqs]
        self.prompt = prompt
        self.continuations = continuations

    @property
    def token_scores(self):
        return [s.logprobs for s in self.seqs]

    def scores(self, agg="sum", **kwargs):
        """
        Returns the sequence scores per continuation.

        Aggregates sequences by the provided 'agg' method:

        - 'sum': Sum of logprobs (product of probabilities), S = sum(logprobs)
        - 'mean': mean of logprobs, S = sum(logprobs) / len(seq)
        - 'normalized': length-normalized sum of logprobs, S = sum(logprobs) / (len(seq) ** alpha)
        """
        if agg == "sum":
            return np.array([s.logprobs.sum() for s in self.seqs])
        elif agg == "mean":
            return np.array([s.logprobs.mean() for s in self.seqs])
        elif agg.startswith("normalized"):
            alpha = kwargs.get("alpha", 0.7)
            seq_lens = np.array([len(s) for s in self.seqs])
            sum_scores = np.array([s.logprobs.sum() for s in self.seqs])
            return sum_scores / (seq_lens ** alpha)
        else:
            raise ValueError("invalid aggregation: {}".format(agg))

    def logprobs(self, agg="sum"):
        normalized = nputil.log_softmax(self.scores(agg))
        return normalized

    def probs(self, agg="sum"):
        return np.exp(self.logprobs(agg))

    def argmax(self, agg="sum") -> str:
        return self.continuations[self.scores(agg=agg).argmax()]

    def __str__(self):
        return "\n".join([f"-{c}: {score}" for c,score in zip(self.continuations, self.scores(agg="sum"))])

async def dc_score(model: dc.DcModel, prompt, values, *args, **kwargs):
    if type(values) is str:
        values = [values]

    prompt_seq = dc.seq(model.tokenizer.tokenize(prompt, asbytes=True))
    value_ids = [model.tokenizer.tokenize(value, asbytes=True) for value in values]

    kwargs.pop("internal", None)
    all_tokens = []
    all_scores = []

    kwargs["noscore"] = False
    return ScoringResult(prompt, values, await model.score([prompt_seq] * len(value_ids), value_ids, *args, **kwargs))