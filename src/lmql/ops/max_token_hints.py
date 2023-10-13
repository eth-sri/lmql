"""
Utility functions for working with max_tokens hints
as produced by LMQL constraint operations.
"""
from typing import List, Dict

TokenHint = Dict[str, int]

def dict_min_token_hint(hints: List[TokenHint]) -> TokenHint:
    """
    Takes the element-wise minimum of the given token hints.
    """
    if len(hints) == 0:
        return {}
    elif len(hints) == 1:
        return hints[0]
    else:
        merged = {}
        for h in hints:
            for k,v in h.items():
                if v != 0:
                    merged[k] = min(h.get(k, v), v)
        return merged
    
def concrete_hints(hints: dict):
    """
    Returns the concrete hints from the given list of token hints.
    """
    return {k:v for k,v in hints.items() if v != 0}
    
def most_restrictive_hint(hints: List[int]):
    """
    Takes the element-wise minimum of the given token hints.
    """
    concrete = [h for h in hints if h != 0]
    if len(concrete) == 0:
        return 0
    else:
        return min(concrete)