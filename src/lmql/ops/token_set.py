import re
import atexit

from tokenize import Token
from typing import Iterable, Tuple
from itertools import product

from lmql.utils import nputil
import numpy as np
from lmql.runtime.stats import Stats

def get_vocab(tokenizer):
    if hasattr(tokenizer, "vocab"):
        return tokenizer.vocab
    elif hasattr(tokenizer, "get_vocab"):
        return tokenizer.get_vocab()
    elif hasattr(tokenizer, "tokenizer_impl"):
        return get_vocab(tokenizer.tokenizer_impl)
    else:
        assert False, "Could not obtain full vocabulary from unknown tokenizer type: {}".format(type(tokenizer))

class VocabularyMatcher:
    """
    Generates sub-token level logit masks from provided tokens.
    """
    def __init__(self, tokenizer, model_identifier):
        self.tokenizer = tokenizer
        self.model_identifier = model_identifier
        self.vocab = {v: k for k, v in get_vocab(self.tokenizer).items()}

        # TODO: this should be more complete
        self.space_repr = self.tokenizer.tokenize(" ")[0]
        self.nl_repr = self.tokenizer.tokenize("\n")[0]
        
        self.token_lengths = None

        self.stats = Stats("VocabularyMatcher")
        self.disk_cached = 0

    @property
    def eos_token_id(self):
        return self.tokenizer.eos_token_id

    @staticmethod
    def init(tokenizer):
        if VocabularyMatcher._instance is not None:
            return

        # first try to load pickled matcher from cache (faster)
        import pickle
        import pathlib

        cache_dir = pathlib.Path.home() / ".cache" / "lmql"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_identifier = tokenizer.model_identifier.replace("/", "-")
        cache_path = cache_dir / f"token-mask-cache-{cache_identifier}.pkl"
        matcher_path = cache_dir / f"matcher-{cache_identifier}.pkl"

        try:
            with open(matcher_path, "rb") as f:
                VocabularyMatcher._instance = pickle.load(f)
                VocabularyMatcher._instance.stats = Stats("VocabularyMatcher")
        except:
            VocabularyMatcher._instance = VocabularyMatcher(tokenizer, tokenizer.model_identifier)

        if cache_path.exists():
            with open(cache_path, "rb") as f:
                try:
                    import time
                    s = time.time()
                    VocabularyMatcher.cache = pickle.load(f)
                    VocabularyMatcher._instance.disk_cached = len(VocabularyMatcher.cache)
                    # print("Matcher cache loaded in {}s".format(time.time() - s))
                except:
                    print("Failed to load token mask cache from {}. If the cache is corrupted, please delete it.".format(cache_path))

        atexit.register(lambda: VocabularyMatcher._instance.save())

    def save(self):
        # save cache to disk
        import pickle
        import pathlib

        # assert False

        cache_dir = pathlib.Path.home() / ".cache" / "lmql"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_identifier = self.model_identifier.replace("/", "-")
        cache_path = cache_dir / f"token-mask-cache-{cache_identifier}.pkl"
        matcher_path = cache_dir / f"matcher-{cache_identifier}.pkl"

        with open(matcher_path, "wb") as f:
            stats = self.stats
            self.stats = None
            pickle.dump(self, f)
            self.stats = stats

        def is_cached(k):
            if k.startswith("named:"):
                return True
            if k.startswith("charlen:"):
                return True
            return False

        with open(cache_path, "wb") as f:
            pickle.dump({k: v for k, v in VocabularyMatcher.cache.items() if is_cached(k)}, f)

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

    @staticmethod
    def with_cache(keys, provider):
        keys = [k for k in keys if k is not None]
        for k in keys:
            if k in VocabularyMatcher.cache.keys():
                return VocabularyMatcher.cache[k]
        else:
            result = provider()
            for k in keys:
                VocabularyMatcher.cache[k] = result
            return result

    def mask_cache_name(self, tokens=None, regex=None, minus=None, prefix=None, exact=None, charlen=None, name=None):
        keys = ["named:" + name] if name is not None else []
        if regex is not None:
            return keys + ["regex:"]
        elif charlen is not None:
            return keys + ["charlen:" + str(charlen)]
        else:
            assert tokens is not None
            t = ("prefix " if prefix else "") + ("* \ " if minus else "") + "|".join(sorted(list(tokens)))
            return keys + [t]

    def make_mask(self, tokens=None, regex=None, minus=None, prefix=False, exact=False, charlen=None, name=None):
        with self.stats.timer("make_mask"):
            cache_keys = self.mask_cache_name(tokens, regex, minus, prefix, exact, charlen, name)
            
            def do_make_mask():
                if tokens is not None:
                    mask = self._make_mask_from_tokens(tokens, prefix, exact=exact)
                elif charlen is not None:
                    mask = self._make_mask_from_char_length(charlen)
                else:
                    assert regex is not None, "TokenSetConcrete: either tokens or regex must be set."
                    assert not prefix, "TokenSetConcrete: prefix is not supported for regex."
                    mask = self._make_mask_from_regex(regex)

                if minus: mask = np.logical_not(mask)

                return mask
            
            return VocabularyMatcher.with_cache(cache_keys, do_make_mask)

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

    def _make_mask_from_char_length(self, length):
        if self.token_lengths is None:
            token_lengths = np.zeros([self.vocab_size], dtype=np.int32)
            for id, subtoken in self.vocab.items():
                token_lengths[id] = len(subtoken)
            self.token_lengths = token_lengths
        
        return self.token_lengths == length

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

        def tstr(t):
            return str([t])[1:-1]

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
                tokens.append(tstr(s))

        return prefix + "{{{}}}".format(
            ", ".join([t for t in sorted(list(tokens))]) + ("..." if truncated else "")
        )

VocabularyMatcher._instance = None
VocabularyMatcher.cache = {}

class TokenSetConcrete:
    def __init__(self, tokens=None, minus=False, mask=None, regex=None, prefix=False, exact=False, charlen=None, name=None):
        VocabularyMatcher.ensure_ready()

        if mask is not None:
            self.mask = mask.copy()
        else: 
            self.mask = VocabularyMatcher.instance().make_mask(tokens=tokens, regex=regex, minus=minus, prefix=prefix, exact=exact, charlen=charlen, name=name)

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

def tset(*tokens, regex=False, prefix=False, exact=False, charlen=None, name=None):
    if charlen is not None:
        return TokenSet(charlen=charlen, name=name)
    if regex:
        assert len(tokens) == 1, "cannot create a TokenSet from multiple regexes."
        return TokenSet(regex=tokens[0], name=name)
    if len(tokens) == 1 and type(tokens[0]) is set:
        return TokenSet(set(list(tokens[0])), minus=False, name=name)
    return TokenSet(set(tokens), minus=False, prefix=prefix, exact=exact, name=name)

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