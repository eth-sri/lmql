import lmql.utils.nputil as nputil
import numpy as np

class TokenDistribution:
    """
    Token distribution mapping arbitrary token representations to log-probabilities.
    """
    def __init__(self):
        self.probs = {}
    
    def __setitem__(self, key, value):
        if type(key) is int:
            key = [key]
            value = [value]
        elif type(key) is str:
            key = [key]
            value = [value]
        elif type(key) is np.ndarray and key.dtype == np.bool_:
            key = np.where(key)[0]

        key = nputil.ensure_iterable(key)
        value = nputil.ensure_iterable(value)

        key, value = self.broadcast(key, value)

        for k,v in zip(key, value):
            self.probs[k] = v

    def broadcast(self, a, b):
        if len(a) == len(b):
            return a, b
        if len(a) == 1:
            return [a[0] for _ in range(len(b))], b
        elif len(b) == 1:
            return a, [b[0] for _ in range(len(a))]
        else:
            raise ValueError("Cannot broadcast arrays of length {} and {}".format(len(a), len(b)))

    def __repr__(self) -> str:
        return "<TokenDistribution: {}>".format(self.probs)
    
    def sample(self, num_samples=1):
        """
        Samples multinomially from the distribution.
        """
        items = list(self.probs.items())
        keys = [k for k, v in items]
        logprobs = nputil.log_softmax([v for k, v in items])
        
        key_ids, scores = nputil.multinomial(logprobs, num_samples=num_samples)

        return [keys[i] for i in key_ids], scores
    
    def score(self, tokens):
        """
        Returns the logprobs of the provided 'tokens'

        Args:
            tokens (list): List of tokens to get logprobs for.
        """
        return [self.probs[t] for t in tokens]

    def topk(self, k=1):
        """
        Returns the top-k tokens and their logprobs.
        """
        items = list(self.probs.items())
        keys = [k for k, v in items]
        logprobs = np.array([v for k, v in items])
        
        k = min(k, len(logprobs))
        
        scores, key_ids = nputil.topk(logprobs, k=k, sorted=True)

        return [keys[i] for i in key_ids], scores