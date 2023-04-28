# from lmql.tests.expr_test_utils import *
from lmql.ops.ops import Sentences, NextToken
from lmql.ops.token_set import VocabularyMatcher
from transformers import AutoTokenizer

# enable_show_transformed()

def test_sentences_op():
    VocabularyMatcher.init(AutoTokenizer.from_pretrained("gpt2"))

    op = Sentences([])

    assert op.forward("This is a test. Another sentence. This is incomplete") == ('This is a test.', ' Another sentence.', ' This is incomplete')

    assert str(op.follow("This is a test" + NextToken)) == "{eos} -> ('This is a test',) and * -> ('This is a test<lmql.next>',)"
    assert str(op.follow("This is a test." + NextToken)) == "{eos} -> ('This is a test.',) and * -> ('This is a test.', '<lmql.next>')"



test_sentences_op()