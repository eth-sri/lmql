import numpy as np

def is_array(x):
    return isinstance(x, np.ndarray)

def item(a):
    if is_array(a): 
        assert len(a) == 1 and a.ndim == 1
        return a[0]
    else: return a

def ensure_array(v, dtype=None):
    if v is None: return None
    if is_array(v): return v
    else: return np.array(v, dtype=dtype)


def log_softmax(a):
    return a - np.log(np.sum(np.exp(a)))

def topk(a, k:int, sorted: bool = False, axis=-1):
    assert k > 0, "topk(): k must be > 0"
    idx = np.argpartition(a, -k, axis=axis)[..., -k:]
    if sorted: 
        index_values = np.take_along_axis(a, idx, axis=axis)
        idx = np.take_along_axis(idx, np.argsort(index_values, axis=axis), axis=axis)
        # reverse order of indices 
        idx = idx[..., ::-1]
    values = np.take_along_axis(a, idx, axis=axis)
    return values, idx

def multinomial(logprobs, num_samples=1):
    if num_samples == 0:
        return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
    # renormalize logprobs
    logprobs = logprobs - np.log(np.exp(logprobs).sum())
    probs = np.exp(logprobs)

    num_samples_i = min(num_samples, len(logprobs), (logprobs > -np.inf).sum())
    next_token_id = np.random.choice(len(logprobs), p=probs, size=num_samples_i, replace=False)
    next_token_score = logprobs[next_token_id]

    return next_token_id, next_token_score

def unsqueeze(a, axis):
    if is_array(a):
        return np.expand_dims(a, axis)
    else:
        return a
    
def replace_inf_nan_with_str(d):
    import math

    if type(d) is dict:
        for k, v in d.items():
            d[k] = replace_inf_nan_with_str(v)
        return d
    elif type(d) is list:
        for i, v in enumerate(d):
            d[i] = replace_inf_nan_with_str(v)
        return d
    elif type(d) is float:
        if math.isinf(d) or math.isnan(d):
            return str(d)
    return d
