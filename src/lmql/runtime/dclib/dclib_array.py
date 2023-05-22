from typing import List, Any
import asyncio
from typing import Optional
from dataclasses import dataclass
from abc import abstractclassmethod, abstractmethod

import numpy as np
from lmql.utils import nputil

@dataclass
class Continuation:
    token: Any
    logprob: Any
    user_data: Any
class criterion: 
    def __and__(self, other):
        return logical_and(self, other)

    def __or__(self, other):
        return logical_or(self, other)

    def __not__(self):
        return logical_not(self)

class logical_not(criterion):
    def __init__(self, a):
        self.a = a
    def __call__(self, seq):
        return not self.a(seq)

class logical_and(criterion):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def __call__(self, seq):
        return self.a(seq) and self.b(seq)

class logical_or(criterion):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def __call__(self, seq):
        return self.a(seq) or self.b(seq)


class eos_criterion(criterion): 
    def __call__(self, seq):
        return seq.is_done()
eos = eos_criterion()

class ge(criterion):
    def __init__(self, max_len):
        self.max_len = max_len
    def __call__(self, seq):
        return len(seq) >= self.max_len

class lt(criterion): 
    def __init__(self, max_len):
        self.max_len = max_len
    def __call__(self, seq):
        return len(seq) < self.max_len


class topk_scorer:
    @abstractmethod
    def __call__(self, score, *args, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def score(cls, scores, *args, **kwargs):
        pass


class sum_scorer(topk_scorer):
    def __call__(self, scores, s, *args, **kwargs):
        return self.score(scores, s, *args, **kwargs)

    @classmethod
    def score(cls, scores, s, *args, **kwargs):
        scores = scores[s.prompt_len:]
        if s.data("head.variable") == "__done__" and hasattr(s, "next_ids") and len(s.next_ids) == 0:
            scores = scores[:-1]
        return scores.sum()


class mean_scorer(topk_scorer):
    def __call__(self, scores, s, *args, **kwargs):
        return self.score(scores, *args, **kwargs)

    @classmethod
    def score(cls, scores, s, *args, **kwargs):
        scores = scores[s.prompt_len:]
        if s.data("head.variable") == "__done__" and hasattr(s, "next_ids") and len(s.next_ids) == 0:
            scores = scores[:-1]
        return scores.mean()


class alpha_length_normalized(topk_scorer):
    def __init__(self, alpha=0.7):
        self.alpha = alpha

    def __call__(self, scores, *args, **kwargs):
        return self.score(scores, self.alpha)

    @classmethod
    def score(cls, scores, alpha=0.7, *args, **kwargs):
        if len(scores) == 0:
            return np.array(0.0)
        else:
            return (np.array(1.0) / float(len(scores)) ** alpha) * scores.sum()


class alpha_length_normalized_det(topk_scorer):
    def __init__(self, alpha=0.7):
        self.alpha = alpha

    def __call__(self, scores, s, *args, **kwargs):
        return self.score(scores, s, alpha=self.alpha)

    @classmethod
    def score(cls, scores, s, alpha=0.7, *args, **kwargs):
        scores = scores[s.prompt_len:]
        det = s.deterministic[s.prompt_len:]
        if s.data("head.variable") == "__done__" and hasattr(s, "next_ids") and len(s.next_ids) == 0:
            scores = scores[:-1]
            det = det[:-1]
        score_det = alpha_length_normalized.score(scores[det], alpha)
        score_act = alpha_length_normalized.score(scores[~det], alpha)
        return score_det + score_act


def max_score(ar, scorer: Optional[topk_scorer]=None):
    """
    Returns the value of the maximum scoring sequence in ar.
    """
    assert len(ar) > 0, "dc.max_score is not defined for empty arrays"
    
    if scorer is None:
        scorer = alpha_length_normalized()

    def op_max_score(seqs, score):
        res = np.array([score] + [scorer(s.logprobs, s) for s in seqs])
        return res.max()

    return ar.reduce(op_max_score, np.finfo(np.float32).min)

def min_score(ar, scorer: Optional[topk_scorer]=None):
    """
    Returns the value of the minimum scoring sequence in ar.
    """
    assert len(ar) > 0, "dc.min_score is not defined for empty arrays"

    if scorer is None:
        scorer = alpha_length_normalized()

    def op_max_score(seqs, score):
        return np.array([score] + [scorer(s.logprobs, s) for s in seqs]).min()

    return ar.reduce(op_max_score, np.finfo(np.float32).max)

def array_sorted(ar, key, name=None):
    def op_sorted(seqs):
        if len(seqs) == 0: 
            return None
        return list(sorted(seqs, key=key))
    return ar.element_wise(op_sorted, name=name)

def topk(ar, k, scorer: Optional[topk_scorer]=None, name=None):
    if scorer is None:
        scorer = alpha_length_normalized()
    
    def op_topk(seqs):
        if len(seqs) == 0: 
            return None

        scores = np.stack([scorer(s.logprobs, s) for s in seqs], axis=0)
        _, topk_indices = nputil.topk(scores, min(k, len(scores)))

        return [seqs[i] for i in topk_indices]

    return ar.element_wise(op_topk, name=name)


def seperate_topk(ar, k, scorer: Optional[topk_scorer]=None, name=None):
    if scorer is None:
        scorer = alpha_length_normalized()
    
    def mark_topk(seqs):
        if len(seqs) == 0: 
            return None

        scores = np.stack([scorer(s.logprobs, s) for s in seqs], axis=0)
        _, topk_indices = nputil.topk(scores, min(k, len(scores)))
        for i in range(len(seqs)):
            seqs[i].data("_is_topk", i in topk_indices)
        return seqs

    def in_top_k(seqs):
        return [s for s in seqs if s.data("_is_topk")]

    def not_in_top_k(seqs):
        return [s for s in seqs if not s.data("_is_topk")]

    ar = ar.element_wise(mark_topk, name=name)
    ar_in_top_k = ar.element_wise(in_top_k, name=name)
    ar_not_in_top_k = ar.element_wise(not_in_top_k, name=name)
    return ar_in_top_k, ar_not_in_top_k

class ComponentWiseValue:
    def __init__(self, value):
        self.value = value

def componentwise_arg(arg, key):
        if type(arg) is ComponentWiseValue:
            assert key in arg.value, f"key {key} not found in component-wise operand"
            return arg.value[key]
        return arg
    
def componentwise_kwargs(key, **kwargs):
    return {k: componentwise_arg(v, key) for k, v in kwargs.items()}

def assert_shape_match(a, b, op, allow_mismatch_keys=False):
    assert type(a) is dict, "internal error: can only perform shape checks on dicts of lists, but got a {}".format(type(a))
    
    if type(b) is not dict:
        raise ValueError(f"cannot apply {op} to a grid-shaped sequence pool and a non-grid-shaped sequence pool")
    
    if allow_mismatch_keys:
        return True

    missing_keys = []

    for k in set(a.keys()):
        if k not in b:
            missing_keys.append(k)
    
    if len(missing_keys) > 0:
        raise ValueError(f"cannot apply {op} to two grid-shaped sequence pools with different sets of keys {a.keys()} vs. {b.keys()} (dimensions in a but not b: {missing_keys})")

    return True

class NoDim: pass

def apply_componentwise(op, a, b, opname, allow_mismatch_keys=False, default_value=None):
    assert_shape_match(a, b, opname, allow_mismatch_keys=allow_mismatch_keys)

    pools_a = dict(a.items() if type(a) is dict else [(NoDim, a)])
    pools_b = dict(b.items() if type(b) is dict else [(NoDim, b)])

    all_keys = set(pools_a.keys()).union(set(pools_b.keys()))
    result = {}

    for k in all_keys:
        pool_a = pools_a[k] if k in pools_a else default_value
        pool_b = pools_b[k] if k in pools_b else default_value

        result[k] = op(pool_a, pool_b)

    return result

class DataArray:
    def __init__(self, data, dims=None):
        super().__init__()
        
        if type(data) is not dict: data = {NoDim: data}

        try:
            self.dtype = type(list(data.values())[0][0]) if type(data) is dict else type(data)
        except:
            self.dtype = 'seq'

        self.sequences = data
        self.shape = dims

    @property
    def paths(self):
        return self.sequences.keys()

    def reduce(self, op, accumulated=None, *args, **kwargs):
        for element in self.sequences.values():
            if element is None: continue
            accumulated = op(element, accumulated, *args, **kwargs)
        return accumulated
    
    def name(self, name=None, nopath=False):
        """
        Names the sequences in this pool with the given name. 
        This information is useful for debugging purposes.

        Parameters:
            name (str): The name to give to the sequences in this pool.
            nopath (bool): If True, the name will not be suffixed with the path of the sequence in the pool (e.g. <name>.dim1.dim2).
        """
        if name is None:
            return self
        
        for path, result in self.sequences.items():
            if result is None:
                continue
            for s in result:
                if hasattr(s, "pool"):
                    if path is NoDim or nopath:
                        s.pool = name
                    else:
                        s.pool = name + "." + ".".join(path)
        return self

    def element_wise(self, op, name=None, *args, **kwargs):
        def op_with_path(path, element, *args, **kwargs):
            return path, op(element, *args, **kwargs)
        result_items = [op_with_path(path, element, *args, **kwargs) for path, element in self.sequences.items()]
        return DataArray(dict([(path,value) for path,value in result_items if value is not None]), dims=self.shape).name(name)

    async def aelement_wise(self, op, *args, **kwargs):
        async def op_with_path(path, element, *args, **kwargs):
            return path, await op(element, *args, **kwargs)
        result_items = await asyncio.gather(*[op_with_path(path, seqs, *args, **kwargs) for path, seqs in self.sequences.items()])
        return DataArray(dict(result_items))

    def extend(self, other):
        def op_extend(p1, p2):
            extended_seqs = []
            for sq, continuation in zip(p1, p2):
                tokens = continuation.token.reshape(-1)
                logprobs = continuation.logprob.reshape(-1)
                user_data = continuation.user_data or [None] * len(tokens)
                for t,s,u in zip(tokens, logprobs, user_data):
                    extended_seqs.append(sq.extend(Continuation(t, s, u)))
            return extended_seqs

        return DataArray(apply_componentwise(op_extend, self.sequences, other.sequences, "extend", allow_mismatch_keys=False), dims=self.shape)

    def separate_by(self, *criteria):
        """
        Separate this bundle intot two bundles (a,b), one containing sequences that satisfy 
        the provided criteria (a), and one containing sequences that do not (b).
        """
        def is_a(seq): return all(c(seq) for c in criteria)
        
        def op_separate(s):
            if s is None: return None, None
            return [s for s in s if is_a(s)], [s for s in s if not is_a(s)]
        tuple_array = self.element_wise(op_separate)

        return tuple_array.element_wise(lambda x: x[0]), tuple_array.element_wise(lambda x: x[1])

    def separate_by_list(self, criterium, reshape=False):
        """
        Separate this bundle into as many bundles as there are unique evaluations of criterium.
        """

        separated_seqs = {}

        for s in self.unstructured():
            key = criterium(s)
            if key in separated_seqs:
                separated_seqs[key].append(s)
            else:
                separated_seqs[key] = [s]

        for key, seqs in separated_seqs.items():
            if reshape:
                separated_seqs[key] = DataArray(separated_seqs[key]).reshape(self.shape)
            else:
                separated_seqs[key] = DataArray(separated_seqs[key])

        return separated_seqs

    def __add__(self, other):
        def op_add(s1, s2):
            if s1 is None: return s2
            if s2 is None: return s1
            return [s for s in (s1 + s2) if s is not None]

        result = apply_componentwise(op_add, self.sequences, other.sequences, "+", allow_mismatch_keys=True)
        return DataArray(result)

    def __len__(self):
        return sum(len(p) if p is not None else 0 for p in self.sequences.values())

    def unstructured(self):
        """
        Unstructured iterator function over all sequences in this array.
        """
        for leaf in self.sequences.values():
            if type(leaf) is list:
                for item in leaf:
                    if item is None:
                        continue
                    yield item
            else:
                if leaf is None:
                    continue
                yield leaf

    def flatten(self):
        """
        Returns a flattened DataArray listing all elements of this array in the same dimension.
        """
        return DataArray([s for s in self.unstructured()])

    def item(self, i, path=None):
        """
        Returns item `i` at the given path in this array.
        """
        if path is None:
            assert list(self.sequences.keys())[0] is NoDim, "Cannot access item without path if the array has more than one dimension."
            path = NoDim
        return self.sequences[path][i]

    def items(self, path=None):
        if path is None:
            assert list(self.sequences.keys())[0] is NoDim, "Cannot access item without path if the array has more than one dimension."
            path = NoDim
        for s in self.sequences[path]:
            yield s

    def unique(self):
        """
        Returns a new DataArray with the same shape as this one, but with only unique sequences within each pool.
        """
        return self.element_wise(lambda seqs: list(set(seqs)))

    def filter(self, op):
        """
        Filters the sequences in this array dimension-wise by the given operation.
        """
        def op_filter(seqs):
            r = [s for s in seqs if op(s)]
            if len(r) == 0:
                return None
            else:
                return r
        return self.element_wise(op_filter)

    def reshape(self, *dims):
        """
        Regroup all sequences in this array according to the provided list of dimensions.

        A dimension can be either a string or a callable.
        
        For strings it acts as a getter for the corresponding user data attribute 
        of each sequence (e.g. head.variable).

        For callables it is called with the sequence as argument and should return 
        a unique value by which the sequences are grouped (e.g. lambda s: len(s)).
        """
        if dims is None or (len(dims) == 1 and dims[0] is None):
            return self

        # unpack if necessary
        if len(dims) == 1 and (type(dims[0]) is list or type(dims[0]) is tuple):
            dims = dims[0]
        
        dims_computer = [d if callable(d) else lambda s: s.data(d) for d in dims]

        seqs = [s for s in self.unstructured()]
        dimensions = [tuple(d(s) for d in dims_computer) for s in seqs]
        data = {}
        
        for s,d in zip(seqs, dimensions):
            if d in data: data[d].append(s)
            else: data[d] = [s]

        return DataArray(data, dims=dims)

    async def text(self, sequences=None):
        """Async __str__ which additionally detokenizes sequences for better readability."""
        if sequences is None: 
            sequences = self.sequences
        
        lines = []
        def str_k(k):
            if k is NoDim:  return "NoDim"
            elif k is None: return "None"
            else: return str(k)

        max_len_key = max([len(str_k(k)) for k in sequences.keys()])
        for k in sorted(sequences.keys()):
            dimension_lines = [await s.text() for s in self.sequences[k]]
            for i,l in enumerate(dimension_lines):
                if i == 0:
                    lines.append(str_k(k) + (max_len_key - len(str_k(k)) + 1) * " " + l)
                else:
                    lines.append(" " * max_len_key + " " + l)
        return "\n".join(lines)
    
    async def str(self, sequences=None):
        """Async __str__ which additionally detokenizes sequences for better readability."""
        if sequences is None: 
            sequences = self.sequences
        
        lines = []
        def str_k(k):
            if k is NoDim:  return "NoDim"
            elif k is None: return "None"
            else: return str(k)

        max_len_key = max([len(str_k(k)) for k in sequences.keys()])
        for k in sorted(sequences.keys()):
            dimension_lines = [await s.str() for s in self.sequences[k]]
            for i,l in enumerate(dimension_lines):
                if i == 0:
                    lines.append(str_k(k) + (max_len_key - len(str_k(k)) + 1) * " " + l)
                else:
                    lines.append(" " * max_len_key + " " + l)
        return "\n".join(lines)
    
    def __str__(self, data=None):
        if data is None: data = self.sequences

        if type(data) is list:
            lines = []
            for s in data:
                lines.append(str(s))
            return "\n".join(lines)

        lines = []
        def str_k(k):
            if k is NoDim:  return "NoDim"
            elif k is None: return "None"
            else: return str(k)

        if len(self) == 0:
            return "<empty>"

        paths = [len("\t".join(str_k(k))) for k in data.keys()]
        if len(paths) > 0:
            max_len_path = max([len(str_k(k)) for k in data.keys()])
            for k in sorted(data.keys(), key=lambda k: str_k(k)):
                dimension_lines = self.__str__(data[k]).split("\n")
                dimension_values = str_k(k)
                for i,l in enumerate(dimension_lines):
                    if i == 0:
                        lines.append(f"{dimension_values:{max_len_path}} {l}")
                    else:
                        lines.append(f"{'':{max_len_path}} {l}")
        else:
            lines.append("<empty>")
        return "\n".join(lines)

    def data(self, key=None, value=None, sticky=False):
        def op_data(sqs):
            return [s.data(key, value, sticky=sticky) for s in sqs]
        return self.element_wise(op_data)

def items_hierarchy(d, prefix=[]):
    items = []
    for k,v in d.items():
        k = str(k)
        if type(v) is dict:
            items += items_hierarchy(v, [*prefix, k])
        else:
            items.append((".".join([*prefix, k]), v))
    if len(prefix) == 0:
        return sorted(items, key=lambda x: x[0])
    return items

def seqs(seqs=None):
    return DataArray(seqs)
