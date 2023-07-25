import re
import atexit

from tokenize import Token
from typing import Iterable, Tuple
from itertools import product

from lmql.utils import nputil
import numpy as np
from lmql.runtime.stats import Stats
from lmql.runtime.caching import cachefile, cache_file_exists
from lmql.runtime.tokenizer import get_vocab
from lmql.ops.regex import Regex

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

        cache_identifier = tokenizer.model_identifier.replace("/", "-").replace(":", "__")
        cache_identifier += "-" + type(tokenizer.tokenizer_impl).__name__.replace("[^a-z0-9]", "")
        cache_path = f"token-mask-cache-{cache_identifier}.pkl"
        matcher_path = f"matcher-{cache_identifier}.pkl"

        try:
            with cachefile(matcher_path, "rb") as f:
                VocabularyMatcher._instance = pickle.load(f)
                VocabularyMatcher._instance.stats = Stats("VocabularyMatcher")
        except:
            VocabularyMatcher._instance = VocabularyMatcher(tokenizer, tokenizer.model_identifier)

        if cache_file_exists(cache_path) and False:
            with cachefile(cache_path, "rb") as f:
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

        cache_identifier = self.tokenizer.model_identifier.replace("/", "-")
        cache_identifier += "-" + type(self.tokenizer.tokenizer_impl).__name__.replace("[^a-z0-9]", "")
        cache_path = f"token-mask-cache-{cache_identifier}.pkl"
        matcher_path = f"matcher-{cache_identifier}.pkl"

        with cachefile(matcher_path, "wb") as f:
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

        with cachefile(cache_path, "wb") as f:
            pickle.dump({k: v for k, v in VocabularyMatcher.cache.items() if is_cached(k)}, f)

    @staticmethod
    def instance():
        if VocabularyMatcher._instance is None:
            raise Exception("VocabularyMatcher not initialized.")
        return VocabularyMatcher._instance

    @staticmethod
    def ensure_ready():
        VocabularyMatcher.instance()

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
            return keys + ["regex:" + regex]
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
                    mask = self._make_mask_from_regex(regex, prefix)

                if minus: mask = np.logical_not(mask)

                return mask
            
            return VocabularyMatcher.with_cache(cache_keys, do_make_mask)

    def _make_mask_from_regex(self, regex, prefix=False):
        regex = regex.replace(" ", self.space_repr)
        regex = regex.replace("\n", self.nl_repr)
        regex = regex.replace(" ", self.tokenizer.tokenize(" ")[0])

        mask = np.zeros([self.vocab_size], dtype=np.bool_)
        if prefix:
            r = Regex(regex)
            for id, subtoken in self.vocab.items():
                if r.is_prefix(subtoken):
                    mask[id] = True
        else:
            pattern = re.compile(regex, re.UNICODE)
            for id, subtoken in self.vocab.items():
                if pattern.match(subtoken) is not None:
                    mask[id] = True

        return mask

    @property
    def vocab_size(self):
        return self.tokenizer.vocab_size

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
                        t = re.escape(t)
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
                # invalid token
                if not i in self.vocab:
                    continue

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

def has_tail(mask):
    if mask is None: return False
    if type(mask) is str: return False
    assert type(mask) is TokenSet
    return mask.tail is not None
class TokenSetConcrete:
    def __init__(self, tokens=None, minus=False, mask=None, regex=None, prefix=False, exact=False, charlen=None, name=None, tail=None):
        VocabularyMatcher.ensure_ready()

        if mask is not None:
            self.mask = mask.copy()
        else: 
            self.mask = VocabularyMatcher.instance().make_mask(tokens=tokens, regex=regex, minus=minus, prefix=prefix, exact=exact, charlen=charlen, name=name)

        self._token_str = None
        # for TokenSetSymbolic compatibility
        self.minusset = False

        # long tail, if mask models deterministic token sequence
        self.tail = tail

        # if we in a deterministic long-tailed mask, extract the full tail
        if self.tail is None and prefix and self.mask.sum() == 1 and tokens is not None and len(tokens) == 1:
            tail_str = list(tokens)[0]
            # deterministic_next_id = self.mask.nonzero()[0][0]
            # deterministic_next_subtoken_str = VocabularyMatcher.instance().tokenizer.decode([deterministic_next_id])
            # if len(tail_str) > len(deterministic_next_subtoken_str):
            self.tail = tail_str

    def merge_tail(self, mask, other):
        """
        Check which of the self.tail and other.tail are still valid under 'mask' and 
        returns the merged tail. If no tail is valid, returns None.
        """

        # tails are only defined for deterministic masks
        if mask.sum() != 1:
            return None
        deterministic_id = mask.nonzero()[0][0]

        # check which of self.tail and other.tail are still valid under 'mask'
        available_tails = []
        for m,t in [(self.mask, self.tail), (other.mask, other.tail)]:
            if t is None: 
                continue
            if m[deterministic_id]: 
                available_tails.append(t)
        
        if len(available_tails) == 0: 
            return None
        elif len(available_tails) == 1: 
            return available_tails[0]
        else:
            assert len(available_tails) == 2
            if available_tails[0] != available_tails[1]:
                # find common tail
                for i in range(min(len(available_tails[0]), len(available_tails[1]))):
                    if available_tails[0][i] != available_tails[1][i]:
                        break
                tail_str = available_tails[0][:i]
                if len(tail_str) == 0: return None

                deterministic_next_id = self.mask.nonzero()[0][0]
                deterministic_next_subtoken_str = VocabularyMatcher.instance().tokenizer.decode([deterministic_next_id])
                if len(tail_str) <= len(deterministic_next_subtoken_str):
                    return None
                else: 
                    return tail_str
            return available_tails[0]

    def union(self, other):
        if other == "∅": 
            return TokenSetConcrete(mask=self.mask, tail=self.merge_tail(self.mask, other))
        if other == "*": 
            return "*"

        assert type(other) is TokenSetConcrete, "Can only union over two TokenSetConcrete."

        mask = np.logical_or(self.mask, other.mask)
        return TokenSetConcrete(mask=mask, tail=self.merge_tail(mask, other))

    def intersect(self, other):
        if other == "∅": return "∅"
        if other == "*": return self

        assert type(other) is TokenSetConcrete, "Can only intersect two TokenSetConcrete."


        mask = np.logical_and(self.mask, other.mask)
        return TokenSetConcrete(mask=mask, tail=self.merge_tail(mask, other))
     
    def setminus(self, other):
        if other == "*": 
            return "∅"
        if other == "∅":
            return TokenSetConcrete(mask=self.mask)
        
        assert type(other) is TokenSetConcrete, "Can only setminus two TokenSetConcrete."

        mask = np.logical_and(self.mask, np.logical_not(other.mask))
        return TokenSetConcrete(mask=mask, tail=self.merge_tail(mask, other))
    

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

        if self.tail is not None:
            self._token_str += f" ⤖ '{self.tail}'"
        
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

        return np.all(self.mask == other.mask) and self.tail == other.tail
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
        return TokenSet(regex=tokens[0], prefix=prefix, name=name)
    if len(tokens) == 1 and type(tokens[0]) is set:
        return TokenSet(set(list(tokens[0])), minus=False, name=name)
    return TokenSet(set(tokens), minus=False, prefix=prefix, exact=exact, name=name)

def charlen_tsets():
    l1 = tset(charlen=1)
    token_lengths = VocabularyMatcher.instance().token_lengths
    assert token_lengths is not None, "VocabularyMatcher.instance().token_lengths is None even though it should be fully initialized."
    # get unique values in token_lengths (numpy)
    length_values = np.unique(token_lengths)
    tsets = {int(l): tset(charlen=l) for l in length_values}
    # only eos should have charlen 0
    tsets[0] = tset("eos") 
    return tsets

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