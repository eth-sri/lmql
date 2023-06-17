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

def ensure_iterable(v):
    if type(v) is np.float32 or type(v) is np.float64 or type(v) is np.int32 or type(v) is np.int64 or type(v) is float or type(v) is int or type(v) is str:
        return [v]
    elif type(v) is np.ndarray:
        if v.ndim == 0:
            return [v.item()]
        else:
            return v
    elif type(v) is list:
        return v
    elif hasattr(v, "numpy"):
        return ensure_iterable(v.numpy())
    else:
        assert False, f"ensure_iterable(): type {type(v)} cannot be converted to iterable"


def log_softmax(a, axis=-1):
    a = ensure_array(a)
    # check for log div by zero
    normalizer = np.sum(np.exp(a), axis=axis)
    if (normalizer == 0).any():
        # assign 1.0 to max value
        return np.where(a == np.max(a), 0.0, -np.inf)
    if len(a.shape) > 1:
        normalizer = normalizer.reshape(-1,1)
    return a - np.log(normalizer)

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
