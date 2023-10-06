from typing import Iterable, Tuple, List
import re
import sre_parse
import sre_constants as c
import sys
from copy import copy

CATEGORY_PATTERNS = {c.CATEGORY_DIGIT: re.compile(r'\d'),
                     c.CATEGORY_NOT_DIGIT: re.compile(r'\D'),
                     c.CATEGORY_SPACE: re.compile(r'\s'),
                     c.CATEGORY_NOT_SPACE: re.compile(r'\S'),
                     c.CATEGORY_WORD: re.compile(r'\w'),
                     c.CATEGORY_NOT_WORD: re.compile(r'\W'),}


def _deparse(seq):
    if seq is None: return seq
    pattern = ""
    for op, arg in seq:
        if op == c.ANY:
            pattern += '.'
        elif op == c.LITERAL:
            if chr(arg) in sre_parse.SPECIAL_CHARS:
                pattern += '\\'
            pattern += chr(arg)
        elif op == c.MAX_REPEAT:
            min, max, item = arg
            pattern += _deparse(item)
            if min == 0 and max == c.MAXREPEAT: pattern += "*"
            elif min == 0 and max == 1: pattern += "?"
            elif min == 1 and max == c.MAXREPEAT: pattern += "+"
            elif min == max == 1: pass
            elif min == max: pattern += "{"+str(min)+"}"
            else: pattern += "{"+str(min)+","+str(max)+"}"
        elif op == c.AT and arg == c.AT_END:
            pattern += "$"
        elif op == c.SUBPATTERN:
            arg0, arg1, arg2, sseq = arg
            pattern += '(' + _deparse(sseq) + ')'
        elif op == c.BRANCH:
            must_be_none, branches = arg
            pattern += '|'.join([_deparse(a) for a in branches])
        elif op == c.RANGE:
            low, high = arg
            pattern += chr(low) + '-' + chr(high)
        elif op == c.IN:
            assert isinstance(arg, list)
            if len(arg) == 1 and arg[0][0] == c.CATEGORY:
                pattern += _deparse(arg)
            else:
                pattern += '[' + ''.join([_deparse([a]) for a in arg]) + ']'
        elif op == c.CATEGORY:
            pattern += CATEGORY_PATTERNS[arg].pattern
        elif op == c.NEGATE:
            pattern += '^'
        elif op == c.GROUPREF:
            pattern += f"\\{arg}"
        else:
            assert False, f"unsupported regex pattern {op} with arg {arg}"
    return pattern

def _parse(pattern):
    seq = sre_parse.parse(pattern)
    assert isinstance(seq, sre_parse.SubPattern)
    seq = list(seq)
    return seq

def _subgroups(seq, groupid, value=None, remove=False):
    out = []
    is_int = isinstance(groupid, int)
    for op, arg in seq:
        if op == c.GROUPREF:
            if arg == groupid:
                if value is not None:
                    out.extend(value)
                if remove:
                    continue
            elif is_int and isinstance(arg, int) and remove and arg > groupid:
                arg -= 1
        out.append((op, arg))
    return out

def _consume_char(char, seq, verbose=False, indent=0):
    assert isinstance(seq, list)
    
    def _ret(out, is_consumed=True):
        if out is None: is_consumed = False
        if verbose: print(f'-> {out}({is_consumed})')
        return out, is_consumed

    if len(seq) == 0: return _ret([], False)
    op, arg = seq[0]
    if verbose: print(' '*indent + f"{seq} -{char}-> Operator {op}", end='') 

    if op == c.ANY:
        return _ret(seq[1:])
    elif op == c.LITERAL:
        if arg == char: return _ret(seq[1:])
        else:
            return _ret(None)
    elif op == c.IN:

        negate = False 
        patterns = arg
        if arg[0][0] == c.NEGATE:
            negate = True
            patterns = arg[1:]
        
        match_found = False
        for a in patterns:
            if a[0] == c.LITERAL:
                match_found = (a[1] == char)
            elif a[0] == c.RANGE:
                match_found = (a[1][0] <= char <= a[1][1])
            elif a[0] == c.CATEGORY:
                if a[1] in CATEGORY_PATTERNS:
                    match_found = CATEGORY_PATTERNS[a[1]].fullmatch(chr(char)) is not None
                else:
                    raise NotImplementedError(f"unsupported regex pattern {op}{a}")
            else:
                raise NotImplementedError(f"unsupported regex pattern {op}{a}")
            if match_found: break
        if match_found != negate: # xor -> either match and not negate or no match and negate
            return _ret(seq[1:])
        else: return _ret(None)
        low, high = arg[0][1]
        if low <= char <= high: return _ret(seq[1:])
        else: return _ret(None)
    elif op == c.BRANCH:
        must_be_none, branches = arg
        assert must_be_none is None
        branches_out = []
        for i, branch in enumerate(branches):
            dbranch, _ = _consume_char(char, list(branch), verbose=verbose, indent=indent+2)
            if dbranch is not None: branches_out.append(dbranch)
        if len(branches_out) == 0: return _ret(None)
        out = _simplify([(op, (must_be_none, branches_out))])
        out.extend(seq[1:])
        return _ret(out)
    elif op == c.SUBPATTERN:
        groupid, arg1, arg2, sseq = arg
        groupvalue = []
        assert arg1==0 and arg2==0
        assert isinstance(sseq, (sre_parse.SubPattern, list))
        sseq = list(sseq)
        dsseq, is_consumed = _consume_char(char, sseq, verbose=verbose, indent=indent+2)
        if not is_consumed and len(seq) > 1:
            rest = _subgroups(seq[1:], groupid, remove=True)
            return _consume_char(char, rest, verbose=verbose, indent=indent+2)
        if dsseq is None:
            return _ret(None)
        groupvalue.append((c.LITERAL, char))
        if verbose: print(f" group {groupid} = {groupvalue}")
        if len(dsseq) == 0:
            return _ret(seq[1:])
        out = _simplify([(op, (groupid, arg1, arg2, dsseq))])
        rest = _subgroups(seq[1:], groupid, value=groupvalue, remove=(len(out)==0))
        out.extend(rest)
        return _ret(out)
    elif op == c.MAX_REPEAT:
        min_occr, max_occr, sseq = arg
        sseq = list(sseq)
        dsseq, _ = _consume_char(char, sseq, verbose=verbose, indent=indent+2)
        if dsseq is None:
            if min_occr == 0:
                # could not consume optional character
                # but could recover with next
                return _ret(*_consume_char(char, seq[1:], verbose=verbose, indent=indent))
            else: return _ret(None)
        min_occr = max(min_occr - 1, 0)
        if max_occr != c.MAXREPEAT:
            max_occr = max(max_occr - 1, min_occr)
        out = dsseq
        if max_occr > 0:
            out += [(op, (min_occr, max_occr, sseq))]
        return _ret(out + seq[1:])
    else:
        raise NotImplementedError(f"unsupported regex pattern {op}")

def _simplify(seq, remove_groups=False):
    def _simplify_op(op, arg):
        if op == c.BRANCH:
            must_be_none, branches = arg
            branches = list(map(_simplify, branches))
            if len(branches) == 1:
                return branches[0]
            if len(branches) == 2:
                branches.sort(key=len)
                if len(branches[0]) == 0:
                    b = branches[1]
                    if len(b) > 1:
                        b = [(c.SUBPATTERN, (1, 0, 0, b))]
                    arg = 0, 1, b # min, max, item
                    op = c.MAX_REPEAT
                    return op, arg
            arg = must_be_none, branches
        elif op == c.SUBPATTERN:
            arg0, arg1, arg2, sseq = arg
            sseq = _simplify(sseq)
            if len(sseq) == 0:
                return None
            if remove_groups and len(sseq) == 1 and sseq[0][0] != sre_parse.BRANCH:
                return sseq[0]
            arg = arg0, arg1, arg2, sseq
        return op, arg

    seq_out = []
    for op, arg in seq:
        out = _simplify_op(op, arg)
        if out is None: continue
        elif isinstance(out, list):
            for op, arg in out:
                seq_out.append((op, arg))
        else:
            op, arg = out
            seq_out.append((op, arg))
    return seq_out

class Regex:

    def __init__(self, pattern, cache=True):
        self.pattern = pattern
        self._complied = None
        self._seq = None
        self._trie = {} # hand-rolled dict-base trie; might be good to replace with library
        self.use_cache = cache

    @property 
    def compiled_pattern(self):
        if self._complied is None:
            self._complied = re.compile(self.pattern, re.UNICODE)
        return self._complied

    @property 
    def seq(self):
        if self._seq is None:
            self._seq = _parse(self.pattern)
        return copy(self._seq)
    
    def _check_cache(self, chars):
        if not self.use_cache: return False
        t = self._trie
        for i, c in enumerate(chars):
            if c in t: t = t[c]
            else:
                if '__hit__' in t: return True
                break
        return False
    
    def _cache_add(self, chars):
        if self.use_cache:
            t = self._trie
            for c in chars:
                if c not in t: t[c] = dict()
                t = t[c]
            t['__hit__'] = True
            
    
    def _consume(self, text, verbose=False):
        chars = [ord(c) for c in text]
        if self._check_cache(chars): return None
        seq = self.seq
        for i, char in enumerate(chars):
            seq, is_consumed = _consume_char(char, seq, verbose=verbose)
            if seq is None or not is_consumed:
                self._cache_add(chars[:(i+1)])
                return None
        return seq

    def is_empty(self):
        return self.pattern == ''

    def is_prefix(self, text, verbose=False):
        seq = self._consume(text, verbose=verbose)
        return (seq is not None)

    def d(self, text, verbose=False):
        seq = self._consume(text, verbose=verbose)
        if seq is None: return None
        seq = _simplify(seq)
        return Regex(_deparse(seq))
    
    def simplify(self, remove_groups=True):
        seq = _simplify(self.seq, remove_groups=remove_groups)
        return Regex(_deparse(seq))
   
    def fullmatch(self, text):
        return self.compiled_pattern.fullmatch(text) is not None

    def compare_pattern(self, pattern):
        return _deparse(_simplify(_parse(self.pattern))) == _deparse(_simplify(_parse(pattern)))
    
    def __repr__(self):
        return f"Regex({self.pattern})"
    
if __name__ == "__main__":
    
    assert Regex(r"[1-9]*").fullmatch("")
    assert not Regex(r"[1-9]+").fullmatch("")
    assert Regex(r"([0-9])+").fullmatch("22")
    assert not Regex(r"([0-9])+").fullmatch("a")

    assert Regex(r"[1-9]*").is_prefix("")
    assert Regex(r"[1-9]+").is_prefix("")
    assert Regex(r"([0-9])+").is_prefix("22")
    assert not Regex(r"([0-9])+").is_prefix("a")

    assert Regex(r"abc").d("a").compare_pattern(r"bc")
    assert Regex(r"abc").d("ab").compare_pattern(r"c")
    assert Regex(r"abc").d("b") is None
    assert Regex(r"a{2}bc").d("aa").compare_pattern(r"bc")
    assert Regex(r"a{2}bc").d("a").compare_pattern(r"abc")
    assert Regex(r"a*bc").d("a").compare_pattern(r"a*bc")
    assert Regex(r"a+bc").d("a").compare_pattern(r"a*bc")
    assert Regex(r"a+bc").d("ab").compare_pattern(r"c")
    assert Regex(r"[1-9]a").d("1").compare_pattern(r"a")
    assert Regex(r"[A-Z]a").d("A").compare_pattern(r"a")
    assert Regex(r"[0-9]{4}-[0-9]{2}-[0-9]{2}").d("1993-").compare_pattern(r"[0-9]{2}-[0-9]{2}")
    assert Regex(r"ab").d("ab").compare_pattern(r"")
    assert Regex(r"a+bc").d("a").compare_pattern(r"a*bc")
    assert Regex(r"a?bc").d("b").compare_pattern(r"c")
    assert Regex(r".+c").d("b").pattern == ".*c"
    
    # escape
    assert Regex(r"\.a").d(".").pattern == "a"
    assert Regex(r"\.a").d("a") is None
    
    # branches 
    assert Regex(r"(a|bb)c").d("b").simplify().pattern == "bc"
    assert Regex(r"(b|bb)c").d("b").simplify().compare_pattern(r"b?c")
    assert Regex(r" (a|b)").d(" a").pattern == ""
    assert Regex(r" (a|b) ").d(" a").pattern == " "
    assert Regex(r" (a|b) ").d(" a ").pattern == ""
    assert Regex(r" (a|bb|ab) ").d(" a ").pattern == "" 
    
    # special sequences
    assert Regex(r"\da").d("1").compare_pattern(r"a")
    assert Regex(r"\Da").d("a").compare_pattern(r"a")
    assert Regex(r"\sa").d(" ").compare_pattern(r"a")
    assert Regex(r"\Sa").d("1").compare_pattern(r"a")
    assert Regex(r"\wa").d("1").compare_pattern(r"a")
    assert Regex(r"\Wa").d(" ").compare_pattern(r"a")
    assert Regex(r"a\Wa").d("a").compare_pattern(r"\Wa")
    assert Regex(r"a\wa").d("a").compare_pattern(r"\wa")
    assert Regex(r"a\Sa").d("a").compare_pattern(r"\Sa")
    assert Regex(r"a\sa").d("a").compare_pattern(r"\sa")
    assert Regex(r"a\Da").d("a").compare_pattern(r"\Da")
    assert Regex(r"a\da").d("a").compare_pattern(r"\da")

    # negation
    assert Regex(r"[^A-Z]a").d("1").compare_pattern(r"a")
    assert Regex(r"[^A-Z]a").d("A") is None
    assert Regex(r"a[^A-Z]").d("a").compare_pattern(r"[^A-Z]")

    # backward reference and groups    
    assert Regex(r"(\d+)-\1").d("123-").pattern == r"123"
    assert Regex(r"(\d+)-\1").d("123").pattern == r"(\d*)-123\1"
    assert Regex(r"(\d+)-(\s*)-\2").d("123-").pattern == r"(\s*)-\1" 
    assert Regex(r"(\d+)-(\s*)-\2").d("123").pattern == r"(\d*)-(\s*)-\2"
    assert Regex(r"(?P<test>\d+)-(\s*)-\2(?P=test)").d("123-").pattern == r"(\s*)-\1123" # TODO names work, but are not output
    assert Regex(r"(?P<test>\d+)-(\s*)-\2(?P=test)").d("123").pattern == r"(\d*)-(\s*)-\2123\1"