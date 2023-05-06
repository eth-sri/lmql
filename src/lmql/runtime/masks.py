"""
Utility functions to deal with logit masks.
"""
import numpy as np
from lmql.utils.nputil import is_array

def mask_num_allowed(m):
    """
    Given a logits mask, sets tensor cell value to True iff the corresponding token is allowed according to the mask.
    """
    if type(m) is list:
        assert all([type(x) is int or type(x) is np.int64 for x in m]), "Sparse mask must be a list of int or np.int64"
        return len(m)
    elif type(m) is int or np.isscalar(m):
        return 1
    return np.isclose(m, 0, atol=1e-8).sum()

def mask_is_allowed(m, i):
    if type(m) is list:
        assert all([type(x) is int or type(x) is np.int64 for x in m]), "Sparse mask must be a list of int or np.int64"
        return i in m
    elif type(m) is int or np.isscalar(m):
        return i == int(m)
    return np.isclose(m[i], 0, atol=1e-8)

def mask_get_only_allowed(m):
    if type(m) is list:
        assert all([type(x) is int or type(x) is np.int64 for x in m]), "Sparse mask must be a list of int or np.int64"
        assert len(m) == 1, "only_allowed() only works with masks that allow exactly one token (num_allowed(mask) == 1)"
        return m[0]
    elif type(m) is int or np.isscalar(m):
        return int(m)
    return np.isclose(m, 0, atol=1e-8).argmax()

def is_dense_mask(mask):
    return type(mask) is np.ndarray and all([type(x) is np.float32 or type(x) is np.float64 for x in mask]), "Mask must be a numpy array of floats"

def is_fixed_int_mask(mask):
    return type(mask) is list and len(mask) > 0 and (
        type(mask[0]) is int or type(mask[0]) is np.int64
    )

def to_dense(mask, vocab_size):
    dense_mask = np.ones([vocab_size]) * -np.inf
    dense_mask[mask] = 0
    return dense_mask