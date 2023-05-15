from lmql.ops.token_set import *
from lmql.runtime.tokenizer import load_tokenizer
from lmql.runtime.tokenizers.tiktoken_tokenizer import TiktokenTokenizer
from lmql.tests.expr_test_utils import run_all_tests

t = load_tokenizer("text-davinci-003")
assert type(t.tokenizer_impl) is TiktokenTokenizer
VocabularyMatcher.init(t)

def test_simple():
    t = load_tokenizer("text-davinci-003")

    # simple eos    # 
    s = tset("eos")
    assert t.decode(s.mask.nonzero()[0].tolist()) == "<|endoftext|>"

    # " 0"
    s = tset(" 0$", " 1$", " 2$")
    decoded = t.decode(s.mask.nonzero()[0].tolist())
    assert " 0" in decoded
    assert " 1" in decoded
    assert " 2" in decoded

run_all_tests(globals())