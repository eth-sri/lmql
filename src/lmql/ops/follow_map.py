from typing import Iterable, Tuple
from itertools import product
from lmql.ops.token_set import *

class FollowMap(Iterable):
    def __init__(self):
        self.components = []

    def add(self, component, pattern):
        if type(pattern) is str and pattern != "*":
            pattern = tset(pattern)
        elif type(pattern) is set:
            pattern = tset(*list(pattern))
        self.components.append((pattern, component))

    def __repr__(self):
        return str(self)

    def __str__(self) -> str:
        if len(self.components) == 0:
            return "∅"

        def format_pattern(p):
            if type(p) is set and len(p) == 1:
                return list(p)[0]
            if type(p) is set:
                return sorted(list(p))
            return p

        def format_component(c):
            if type(c) is tuple and len(c) == 2 and type(c[1]) is tuple and len(c[1]) == 1 and c[1][0] in set(["inc", "dec", "fin", "var"]):
                # if c[1][0] == "var":
                #     return c[0]
                return f"{c[1][0]}({c[0]})"
            return c

        return " and ".join(f"{format_pattern(pattern)} -> {format_component(component)}" for pattern, component in self.components)
    
    def __eq__(self, other: object) -> bool:
        assert type(other) is FollowMap, "Can only compare (==) FollowMap instances with other FollowMap instances, not {}".format(type(other))

        return str(other) == str(self)

    def value(self, key):
        for p,c in self:
            if type(p) is set and key in p: 
                return c
            if p == "*": 
                return c
        return None


    def intersect(self, p1):
        """
        TODO: think about intersecting

        (eos) -> None and * -> (How, t)

        with eos

        result should be:

        eos -> None
        
        """

        fm = FollowMap()
        handled = tset()

        for p2, component in self.components:
            assert handled != "*", "Cannot intersect further patterns if '*' has already been handled."
        
            p1 = setminus(p1, handled)
            # p2 = setminus(p2, handled)
            # print("intersect", p1, "and", p2)
            intersected_pattern = intersect(p1, p2)
            # print(" gives", intersected_pattern)
            intersected_pattern = setminus(intersected_pattern, handled)
            # print("minus", handled, " ", intersected_pattern)

            # empty patterns can be skipped
            if intersected_pattern == "∅": continue

            fm.components.append((intersected_pattern, component))
            
            handled = handled.union(intersected_pattern)
            # handled = union(tset(handled), p2)

        # print("intersect fmap", self, "with", p1, "results in", fm)

        return fm

    def add_all(self, other_map):
        for patter, component in other_map.components:
            self.components.append((patter, component))

    def __iter__(self):
        return ((p,c) for p,c in self.components)

    def hashable(self, value):
        if type(value) is tuple:
            return tuple(self.hashable(t) for t in value)
        elif type(value) is ArgTuple:
            return ArgTuple(self.hashable(t) for t in value)
        elif type(value) is list:
            return tuple(self.hashable(t) for t in value)
        elif type(value) is set:
            return tuple(self.hashable(t) for t in value)
        else:
            return value

    def simplify(self):
        by_value = {}
        
        for p,c in self:
            # make component hashable (i.e. tuples => lists)
            c = self.hashable(c)
            if c in by_value:
                by_value[c] = union(by_value[c], p)
            else:
                by_value[c] = p
        
        # # by_pattern = {}
        # # for c,p in by_value.items():
        # #     if p in by_pattern:
        # #         assert by_pattern[p] == c, "Non-unique mapping for pattern {}: {} and {}".format(p, by_pattern[p], c)
        # #     else:
        # #         by_pattern[p] = [c]

        self.components = [(p,c) for c,p in by_value.items()]

    def product(self, *others):
        if len(others) == 0: return self

        result_map = fmap()
        handled = tset()

        pairings = product(*[list(self)] + [list(o) for o in others])

        for mappings in pairings:
            p_intersected = intersect(*[p for p,v in mappings])

            if setminus(p_intersected, handled) == "∅":
                continue

            if p_intersected == "∅": continue
            result_map.add(ArgTuple(v for p,v in mappings), p_intersected)

            handled = handled.union(p_intersected)
        
        result_map.simplify()

        return result_map

    def map(self, fct):
        mappings = [(pattern, fct(pattern, value)) for pattern, value in self.components]
        return fmap(*mappings)
    
    def flat_map(self, fct, simplify=True):
        mappings = []
        
        for pattern, value in self.components:
            submap = fct(pattern, value)
            if submap is None:
                mappings.append((pattern, value))
            else:
                submap = submap.intersect(pattern)
                for subpattern, subvalue in submap.components:
                    mappings.append((subpattern, subvalue))
        result = fmap(*mappings)
        
        if simplify: result.simplify()

        return result


def zip_fmap(*fmaps):
    """
    Simple zip of multiple fmaps (number of components and 
    patterns must match for all fmaps).
    """

    assert len(fmaps) > 0, "cannot zip_fmap with 0 follow maps."
    
    mappings = []
    for entries in zip(*fmaps):
        patterns = [e[0] for e in entries]
        values = tuple([e[1] for e in entries])
        
        assert all([p == patterns[0] for p in patterns])

        mappings.append((patterns[0], values))
    return fmap(*mappings)

def fmap_product(*maps):
    assert len(maps) != 0, "Cannot construct product of zero follow maps."
    return maps[0].product(*maps[1:])

def final_aware_iterator(follow_map):
    for pattern, item in follow_map:
        if type(item) is ArgTuple:
            yield (pattern, (ArgTuple([v[0] for v in item]), [v[1][0] for v in item]))
        else:
            yield pattern, item

class PredeterminedFinal:
    def __init__(self, value, final):
        self.value = value
        self.final = final
    
    def __str__(self):
        return f"{self.final}({self.value})"

def follow_apply(follow_map, op, op_result, context=None):
    value_follow = FollowMap() 

    for pattern, (value, final) in final_aware_iterator(follow_map):
        if type(value) is ArgTuple:
            result_map = op.follow(*value, context=context, result=op_result)
        else:
            result_map = op.follow(value, context=context, result=op_result)

        if result_map is None:
            result_map = fmap(("*", None)).intersect(pattern)
        elif type(result_map) is FollowMap:
            result_map = result_map.intersect(pattern)
        else:
            result_map = fmap(("*", result_map)).intersect(pattern)

        # include final results per component in the result map
        def determine_final(pattern, result):
            if type(result) is PredeterminedFinal:
                return (result.value, [result.final])
            final_unpacked = final
            if type(final) is tuple:
                final_unpacked = list(final)
            return (result, [op.final(final_unpacked, context=context, operands=value, result=result, pattern=pattern)])

        result_map = result_map.map(determine_final)

        value_follow.add_all(result_map)

    value_follow.simplify()
    
    # print("value_follow", value_follow)

    return value_follow

def all_fmap(mapping):
    if type(mapping) is FollowMap: return mapping

    m = FollowMap()
    m.add(mapping, "*")
    return m

def fmap(*mappings):
    m = FollowMap()
    for pattern, result in mappings:
        m.add(result, pattern)
    return m