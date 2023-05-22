from lmql.ops.token_set import *
from lmql.runtime.tokenizer import load_tokenizer
from lmql.tests.expr_test_utils import run_all_tests

VocabularyMatcher.init(load_tokenizer("gpt2"))

def test_simple():
    p1 = ntset("eos")
    p2 = tset("Sunscreen and Drinks", prefix=True)
    r = intersect(p1, p2)
    assert r.tail == "Sunscreen and Drinks", f"Expected 'Sunscreen and Drinks', got '{r.tail}'"

def test_prefix_tail():
    p1 = tset("Sunscreen and Volleyball", prefix=True)
    p2 = tset("Sunscreen and Drinks", prefix=True)
    r = intersect(p1, p2)
    assert r.tail == "Sunscreen and "

def test_different_tails():
    p1 = tset("Sun dscreen and Volleyball", prefix=True)
    p2 = tset("Sunscreen and Drinks", prefix=True)
    r = intersect(p1, p2)
    assert r.tail is None, f"Expected None, got '{r.tail}'"

run_all_tests(globals())