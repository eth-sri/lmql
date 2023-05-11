# -*- encoding: utf-8 -*-
import json
import math
import os
from builtins import str
from itertools import chain

import regex
import six

_DEFAULT_ENCODING = "utf-8"

def _init_encoder():
    with open(os.path.join(os.path.dirname(__file__), 'data/encoder.json'), 'r') as f:
        encoder = json.load(f)
        return encoder

def _get_bpe_merges():
    with open(os.path.join(os.path.dirname(__file__), "data/vocab.bpe"), "r") as f:
        bpe_lines = f.readlines()    
        sliced = bpe_lines[1:len(bpe_lines)-1]
        bpe_merges = [regex.split(r"(\s+)", s) for s in sliced]
        final_merges = []
        for merge in bpe_merges:
            final_merges.append([m for m in merge if len(m.strip()) > 0])
        return final_merges

def _dict_zip(x, y):
    result = {}
    for i in y:
        key = tuple(x[i])
        result[key] = y[i]
    return result

cache = {}

def _encode_string(token):
    return [str(t) for t in list(bytearray(token.encode(_DEFAULT_ENCODING)))]

def _range(x, y):
    res = [val for val in range(y)][x:]
    return res

def _ord(x):
    if not isinstance(x, str):
        x = x.decode(_DEFAULT_ENCODING)
    res = ord(x[0])
    return res

def _get_pairs(word):
    pairs = []
    prev_char = word[0]
    for i in range(1, len(word)):
        ch = word[i]
        pairs.append([prev_char, ch])
        prev_char = ch
    return pairs

def _bpe(token, bpe_ranks):
    if token in cache:
        return cache[token]
    word = list(token)
    pairs = _get_pairs(word)
    if not pairs:
        return token

    while True:
        min_pairs = {}
        for pair in pairs:
            pair_key = tuple(pair)
            rank = bpe_ranks.get(pair_key, float("nan"))
            min_pairs[10e10 if math.isnan(rank) else rank] = pair_key
        bigram = min_pairs[min(map(int, min_pairs.keys()))]
        if not bigram in bpe_ranks:
            break
        bigram = bigram[0], "".join(bigram[1:])
        first = bigram[0]
        second = bigram[1]

        new_word = []
        i = 0

        while i < len(word):
            j = -1
            try:
                j = word.index(first, i)
            except:
                pass
            if j == -1:
                new_word.extend(word[i:])
                break
            new_word.extend(word[i:j])
            i = j
            if word[i] == first and i < len(word)-1 and word[i+1] == second:
                new_word.append(first+second)
                i += 2
            else:
                new_word.append(word[i])
                i += 1

        word = new_word
        if len(word) == 1:
            break
        pairs = _get_pairs(word)
    
    word = ' '.join(word)
    cache[token] = word
    return word


def _bytes_to_unicode():
    bs = list(chain(_range(_ord('!'), _ord('~') + 1), _range(_ord('¡'), _ord('¬') + 1), _range(_ord('®'), _ord('ÿ') + 1)))
    cs = bs[:]
    n = 0
    b = 0
    while b < 2 ** 8:
        if not b in bs:
            bs.append(b)
            cs.append(2 ** 8 + n)
            n += 1
        b += 1

    cs = list(map(lambda x: six.unichr(x), cs))
    result = {}
    for i in range(len(bs)):
        result[str(bs[i])] = cs[i]
    return result
