"""
Thread/Async-local context in the LMQL runtime.
"""

from lmql.runtime.stats import Stats
from contextvars import ContextVar

_tokenizer = ContextVar("tokenizer")
_tokenizer.set([])

def _ensure_tokenizer():
    try:
        _tokenizer.get()
    except LookupError:
        _tokenizer.set([])
    
def get_tokenizer():
    """
    Returns the LMQLTokenizer instance that is currently active in this context.

    This value is set by context in the LMQL interpreter run() function, to enable 
    different tokenizers in sub-queries.
    """
    assert len(_tokenizer.get()) > 0, "No tokenizer set in this context"
    _ensure_tokenizer()
    return _tokenizer.get()[-1]

def set_tokenizer(tokenizer):
    _ensure_tokenizer()
    _tokenizer.set(_tokenizer.get() + [tokenizer])

def pop_tokenizer():
    _ensure_tokenizer()
    _tokenizer.set(_tokenizer.get()[:-1])

class ContextTokenizer:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __enter__(self):
        set_tokenizer(self.tokenizer)
        return self.tokenizer
    
    def __exit__(self, exc_type, exc_value, traceback):
        pop_tokenizer()
        return False