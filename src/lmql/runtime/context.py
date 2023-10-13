"""
Thread/Async-local context information in the LMQL runtime.

Implicit access to an LMQLTokenizer for the current context (e.g. to detokenize input IDs).

Handles nested/sub-queries by maintaining a stack of context objects.
"""

from lmql.runtime.stats import Stats
from contextvars import ContextVar

_context = ContextVar("tokenizer")
_context.set([])

def _ensure_dc_context():
    try:
        _context.get()
    except LookupError:
        _context.set([])

def get_tokenizer():
    """
    Returns the LMQLTokenizer instance that is currently active in this context.

    This value is set by context in the LMQL interpreter run() function, to enable 
    different tokenizers across nested, sub or parallel queries.
    """
    _ensure_dc_context()
    assert len(_context.get()) > 0, "No tokenizer set in this context"
    return _context.get()[-1].tokenizer

def get_truncation_threshold():
    """
    Returns the logprob threshold for truncating logits in the current decoding context.

    This value is set by context in the LMQL interpreter run() function, to enable
    different thresholds across nested, sub or parallel queries.
    """
    _ensure_dc_context()
    assert len(_context.get()) > 0, "No tokenizer set in this context"
    return _context.get()[-1].truncation_threshold

def set_context(tokenizer):
    _ensure_dc_context()
    _context.set(_context.get() + [tokenizer])

def pop_context():
    _ensure_dc_context()
    _context.set(_context.get()[:-1])

class Context:
    def __init__(self, tokenizer, truncation_threshold=-3e38):
        self.tokenizer = tokenizer
        self.truncation_threshold = truncation_threshold

    def __enter__(self):
        set_context(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        pop_context()
        return False