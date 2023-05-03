from lmql.ops.ops import OneOf, NextToken
from lmql.tests.expr_test_utils import run_all_tests
from lmql.ops.follow_map import fmap

def test_one_of():
    one_of = OneOf([])

    assert str(one_of.follow("", set(["abcde", "efgh"]))) == \
        "{abcde, efgh} -> True and * -> False"
    assert str(one_of.follow(NextToken, set(["abcde", "efgh"]))) == \
        "{abcde, efgh} -> True and * -> False"

    assert str(one_of.follow("ab" + NextToken, set(["abcde", "efgh"]))) == \
        "{cde} -> True and * -> False"


run_all_tests(globals())