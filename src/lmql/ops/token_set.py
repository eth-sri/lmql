import re

from tokenize import Token
from typing import Iterable, Tuple
from itertools import product

from lmql.utils import nputil
import numpy as np

def get_vocab(tokenizer):
    if hasattr(tokenizer, "vocab"):
        return tokenizer.vocab
    elif hasattr(tokenizer, "get_vocab"):
        return tokenizer.get_vocab()
    else:
        assert False, "Could not obtain full vocabulary from unknown tokenizer type: {}".format(type(tokenizer))

class VocabularyMatcher:
    """
    Generates sub-token level logit masks from provided tokens.
    """
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.vocab = {v: k for k, v in get_vocab(self.tokenizer).items()}

        # TODO: this should be more complete
        self.space_repr = self.tokenizer.tokenize(" ")[0]
        self.nl_repr = self.tokenizer.tokenize("\n")[0]

    @property
    def eos_token_id(self):
        return self.tokenizer.eos_token_id

    @staticmethod
    def init(tokenizer):
        vm = VocabularyMatcher(tokenizer)
        VocabularyMatcher._instance = vm

    @staticmethod
    def instance():
        if VocabularyMatcher._instance is None:
            raise Exception("VocabularyMatcher not initialized.")
        return VocabularyMatcher._instance

    @staticmethod
    def ensure_ready():
        VocabularyMatcher.instance()

    @property
    def vocab_size(self):
        return len(self.vocab)

    def make_mask(self, tokens=None, regex=None, minus=None, prefix=False, exact=False):
        if tokens is not None:
            mask = self._make_mask_from_tokens(tokens, prefix, exact=exact)
        else:
            assert regex is not None, "TokenSetConcrete: either tokens or regex must be set."
            assert not prefix, "TokenSetConcrete: prefix is not supported for regex."
            mask = self._make_mask_from_regex(regex)

        if minus: mask = np.logical_not(mask)

        return mask

    def _make_mask_from_regex(self, regex):
        regex = regex.replace(" ", self.space_repr)
        regex = regex.replace("\n", self.nl_repr)

        regex = regex.replace(" ", self.tokenizer.tokenize(" ")[0])

        mask = np.zeros([self.vocab_size], dtype=np.bool_)

        pattern = re.compile(regex, re.UNICODE)
        for id, subtoken in self.vocab.items():
            if pattern.match(subtoken) is not None:
                mask[id] = True

        return mask

    def _make_mask_from_tokens(self, tokens, prefix, exact=False):
        mask = np.zeros([self.vocab_size], dtype=np.bool_)

        if "*" in tokens:
            mask[:] = True
        elif len(tokens) > 0:
            if prefix:
                # instead of using the tokens themselves, use subtoken prefixes of the tokens
                tokens = [self.tokenizer(t)["input_ids"][0] for t in tokens]
                for t in tokens: 
                    mask[t] = True
            else:
                if any(t for t in tokens if t != "eos") > 0:
                    def process(t):
                        t = t.replace(".", "\\.")
                        t = t.replace(" ", self.space_repr)
                        t = t.replace("\n", self.nl_repr)
                        return t
                    if exact: 
                        # only allow exact matches
                        pattern = "|".join(f"({process(t)})" for t in tokens if t != "eos")
                        pattern = re.compile(pattern, re.UNICODE)
                        matcher = pattern.fullmatch
                    else:
                        # allow arbitrary further text per token
                        pattern = "|".join(f"{process(t)}.*" for t in tokens if t != "eos")
                        pattern = re.compile(pattern, re.UNICODE)
                        matcher = pattern.match
                    
                    for id, subtoken in self.vocab.items():
                        if matcher(subtoken) is not None:
                            mask[id] = True
                
                if any([t == "eos" for t in tokens]): # has eos
                    mask[self.eos_token_id] = True

        return mask

    def str(self, mask, full=False):
        prefix = ""
        tokens = []
        mask = mask

        if mask.sum() == mask.shape[0]:
            return "*"

        if mask.sum() > np.logical_not(mask).sum() and np.logical_not(mask).sum() > 0:
            prefix = "* \ "
            mask = np.logical_not(mask)

        truncated = False

        # get list of all non-zero indices in self.mask tensor
        for i in mask.reshape(-1).nonzero()[0]:
            if len(tokens) > 5 and not full:
                truncated = True
                break
            if i == self.eos_token_id:
                tokens.append("eos")
            else:
                s = self.vocab[i]
                # replace nl and space
                s = self.tokenizer.convert_tokens_to_string([s])
                s = s.encode("unicode_escape").decode("utf-8")
                tokens.append(s)

        return prefix + "{{{}}}".format(
            ", ".join([t for t in sorted(list(tokens))]) + ("..." if truncated else "")
        )

VocabularyMatcher._instance = None

class TokenSetConcrete:
    def __new__(cls, *args, **kwargs):
        if "mask" in kwargs.keys():
            mask = kwargs["mask"]
            return super(TokenSetConcrete, cls).__new__(cls)
        elif "regex" in kwargs.keys():
            regex = kwargs["regex"]
            key = "regex:" + regex
            if key in TokenSetConcrete.cache.keys():
                return TokenSetConcrete.cache[key]
            else:
                TokenSetConcrete.cache[key] = super(TokenSetConcrete, cls).__new__(cls)
                return TokenSetConcrete.cache[key]
        else:
            tokens = kwargs.get("tokens", args[0])
            assert tokens is not None
        
            minus = kwargs.get("minus", False)
            prefix = kwargs.get("prefix", False)
            
            t = ("prefix " if prefix else "") + ("* \ " if minus else "") + "|".join(sorted(list(tokens)))
            
            if t in TokenSetConcrete.cache.keys():
                return TokenSetConcrete.cache[t]
            else:
                TokenSetConcrete.cache[t] = super(TokenSetConcrete, cls).__new__(cls)
                return TokenSetConcrete.cache[t]

    def __init__(self, tokens=None, minus=False, mask=None, regex=None, prefix=False, exact=False):
        VocabularyMatcher.ensure_ready()

        if mask is not None:
            self.mask = mask.copy()
        else: 
            self.mask = VocabularyMatcher.instance().make_mask(tokens=tokens, regex=regex, minus=minus, prefix=prefix, exact=exact)

        self._token_str = None
        # for TokenSetSymbolic compatibility
        self.minusset = False

    def union(self, other):
        if other == "∅": 
            return TokenSetConcrete(mask=self.mask)
        if other == "*": 
            return "*"

        assert type(other) is TokenSetConcrete, "Can only union over two TokenSetConcrete."

        return TokenSetConcrete(mask=np.logical_or(self.mask, other.mask))

    def intersect(self, other):
        if other == "∅": return "∅"
        if other == "*": return self

        assert type(other) is TokenSetConcrete, "Can only intersect two TokenSetConcrete."

        return TokenSetConcrete(mask=np.logical_and(self.mask, other.mask))
     
    def setminus(self, other):
        if other == "*": 
            return "∅"
        if other == "∅":
            return TokenSetConcrete(mask=self.mask)
        
        assert type(other) is TokenSetConcrete, "Can only setminus two TokenSetConcrete."

        return TokenSetConcrete(mask=np.logical_and(self.mask, np.logical_not(other.mask)))
    

    def starts_with(self, s):
        if s in self.tokens: 
            return not self.minusset # returns True if not minusset and s in self.tokens
        else:
            for s in self.tokens:
                if s.startswith(s): 
                    return not self.minusset # returns True if not minusset and some s in self.tokens starts with s
            return self.minusset

    def __len__(self):
        return self.mask.sum()

    def __repr__(self):
        return str(self)

    def __str__(self, full=False):
        if self._token_str is not None:
            return self._token_str

        self._token_str = VocabularyMatcher.instance().str(self.mask, full=full)
        
        return self._token_str

    def __eq__(self, other):
        if other == "∅": 
            if self.mask.sum() == 0: 
                return True
            return False
        if other == "*": 
            if self.mask.sum() == self.mask.shape[0]: 
                return True
            return False

        assert type(other) is TokenSetConcrete, "Can only compare (==) two TokenSets."

        return np.all(self.mask == other.mask)
TokenSetConcrete.cache = {}

class TokenSetSymbolic:
    def __init__(self, tokens=None, minus=False):
        assert token_set_vocabulary is not None, "TokenSetConcrete: token_set_vocabulary must be set before any TokenSets are instantiated."

        if tokens is None: tokens = set()

        self.tokens = tokens
        self.minusset = minus

    def union(self, other):
        if other == "∅": 
            return TokenSetSymbolic(tokens=self.tokens, minus=self.minusset)
        if other == "*": 
            return "*"

        assert type(other) is TokenSetSymbolic, "Can only union over two TokenSetSymbolics."

        if self.minusset:
            if other.minusset:
                return TokenSetSymbolic(tokens=self.tokens.intersection(other.tokens), minus=True)
            else:
               return TokenSetSymbolic(tokens=self.tokens - other.tokens, minus=True) 
        else:
            if other.minusset:
                return TokenSetSymbolic(tokens=other.tokens - self.tokens, minus=True) 
            else:
                return TokenSetSymbolic(tokens=other.tokens.union(self.tokens), minus=False) 
    
    def intersect(self, other):
        if other == "∅": return "∅"
        if other == "*": return self

        assert type(other) is TokenSetSymbolic, "Can only intersect two TokenSetSymbolics."

        if self.minusset:
            if other.minusset:
                return TokenSetSymbolic(tokens=self.tokens.union(other.tokens), minus=True)
            else:
               return TokenSetSymbolic(tokens=other.tokens - self.tokens, minus=False) 
        else:
            if other.minusset:
                return TokenSetSymbolic(tokens=self.tokens - other.tokens, minus=False) 
            else:
                return TokenSetSymbolic(tokens=self.tokens.intersection(other.tokens), minus=False)

    def setminus(self, other):
        if other == "*": 
            return "∅"
        if other == "∅" or (not other.minusset and len(other.tokens) == 0):
            return TokenSetSymbolic(tokens=self.tokens, minus=self.minusset)
        
        if self.minusset:
            if other.minusset:
                return TokenSetSymbolic(tokens=self.tokens.union(other.tokens), minus=True)
            else:
                excluded_tokens = self.tokens.union(other.tokens)
                return TokenSetSymbolic(tokens=excluded_tokens, minus=True)
        else:
            if other.minusset:
                return TokenSetSymbolic(tokens=self.tokens.intersection(other.tokens), minus=False) 
            else:
                return TokenSetSymbolic(tokens=self.tokens - other.tokens, minus=False)

    def starts_with(self, s):
        if s in self.tokens: 
            return not self.minusset # returns True if not minusset and s in self.tokens
        else:
            for s in self.tokens:
                if s.startswith(s): 
                    return not self.minusset # returns True if not minusset and some s in self.tokens starts with s
            return self.minusset

    def __len__(self):
        if self.minusset: 
            # cannot determine this without knowledge of the vocabulary size
            return 9999
        else: return len(self.tokens)

    def __repr__(self):
        return str(self)

    def __str__(self):
        tokens_str = "{{{}}}".format(", ".join([t for t in sorted(list(self.tokens))]))

        if self.minusset:
            if len(self.tokens) == 0:
                return "*"
            return "* \ {}".format(tokens_str)
        else:
            if len(self.tokens) == 0: 
                return "{}"
            return tokens_str

    def __eq__(self, other):
        if other == "∅": return False
        if other == "*": return False

        assert type(other) is TokenSetSymbolic, "Can only compare (==) two TokenSetSymbolics."

        return other.minusset == self.minusset and str(sorted(list(self.tokens))) == str(sorted(list(other.tokens)))

TokenSet = TokenSetConcrete

def intersect(*args):
    assert len(args) != 0, "Intersection of zero patterns is not possible."
    if len(args) == 1: return args[0]
    if len(args) != 2: return intersect(args[0], intersect(*args[1:]))
    p1, p2 = args

    if p1 == p2: return p1
    
    if p1 == "∅" or p2 == "∅": return "∅"
    if p1 == "*": return p2
    if p2 == "*": return p1
    
    tokens = p1.intersect(p2)
    
    if len(tokens) == 0: return "∅"

    return tokens

def union(p1, p2):
    if p1 == p2: return p1
    
    if p1 == "*": return p1
    if p2 == "*": return p2
    if p1 == "∅": return p2
    if p2 == "∅": return p1

    return p1.union(p2)

def tset(*tokens, regex=False, prefix=False, exact=False):
    if regex:
        assert len(tokens) == 1, "cannot create a TokenSet from multiple regexes."
        return TokenSet(regex=tokens[0])
    if len(tokens) == 1 and type(tokens[0]) is set:
        return TokenSet(set(list(tokens[0])), minus=False)
    return TokenSet(set(tokens), minus=False, prefix=prefix, exact=exact)

def ntset(*tokens):
    if len(tokens) == 1 and type(tokens[0]) is set:
        return TokenSet(set(list(tokens[0])), minus=True)
    return TokenSet(set(tokens), minus=True)

class ArgTuple(tuple): 
    def __repr__(self) -> str:
        return "ArgTuple" + super().__repr__()

def setminus(p1, p2):
    if p1 == "∅": return "∅"
    if p2 == "∅": return p1
    if p1 == "*": p1 = TokenSet(set([]), minus=True)
    
    assert type(p1) is TokenSet
    r = p1.setminus(p2)

    if type(r) is TokenSet and (type(r) is TokenSetSymbolic and not r.minusset and len(r.tokens) == 0):
        return "∅"
    else:
        return r