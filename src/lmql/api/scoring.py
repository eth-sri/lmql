"""
Implements lmql.score and context.score as accessible 
from within LMQL queries.
"""
from typing import List
import numpy as np
import lmql.runtime.dclib as dc
import lmql.utils.nputil as nputil

class ScoringResult:
    """
    Array-view on a set of sequences and their model scores.

    Provides methods to aggregate scores and return the best continuation.
    """

    def __init__(self, prompt, continuations: List[str], num_value_tokens: List[int], seqs: List[dc.seq], model_identifier: str):
        self.seqs = [s.expand() for s in seqs]
        self.prompt = prompt
        # the continuations that were scored
        self.continuations = continuations
        # per continuation, the number of tokens that originate from the appended continuation value
        self.num_value_tokens = num_value_tokens
        self.model_identifier = model_identifier

    @property
    def full_token_scores(self):
        return [s.logprobs for s in self.seqs]

    @property
    def token_scores(self):
        return [s.logprobs[-self.num_value_tokens[i]:] for i,s in enumerate(self.seqs)]

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
        """
        Returns softmax-normalized sequence logprobs per continuation.

        Aggregates sequence scores by the provided 'agg' method:
        """
        normalized = nputil.log_softmax(self.scores(agg))
        return normalized

    def probs(self, agg="sum"):
        """
        Returns softmax-normalized sequence probabilities per continuation.

        Aggregates sequence scores by the provided 'agg' method:
        """
        return np.exp(self.logprobs(agg))

    def argmax(self, agg="sum") -> str:
        """
        Returns the continuation with the highest score.
        """
        return self.continuations[self.scores(agg=agg).argmax()]

    def __str__(self):        
        return "lmql.ScoringResult(model='{}')\n".format(self.model_identifier) + \
            "\n".join([f"-{str([c])[1:-1]}: {score}" for c,score in zip(self.continuations, self.scores(agg="sum"))])

async def dc_score(model: dc.DcModel, prompt, values, **kwargs):
    """
    Internal implementation of lmql.score. For external use, use
    lmql.score and lmql.LLM(..).score instead.
    """
    if type(values) is str:
        values = [values]

    prompt_seq = dc.seq(model.tokenizer.tokenize(prompt, asbytes=True))
    value_ids = [model.tokenizer.tokenize(value, asbytes=True) for value in values]
    num_value_ids = [len(ids) for ids in value_ids]

    kwargs.pop("internal", None)
    all_tokens = []
    all_scores = []

    kwargs["noscore"] = False
    return ScoringResult(prompt, values, num_value_ids, await model.score([prompt_seq] * len(value_ids), value_ids, **kwargs), model.model_identifier)