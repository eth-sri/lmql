from lmql.ops.ops import InOpStrInStr, NextToken
from lmql.tests.expr_test_utils import run_all_tests
from lmql.ops.follow_map import fmap

def test_one_of():
    in_op = InOpStrInStr([])

    result = in_op.follow("abc", "ab" + NextToken)
    assert str(result) == "{c} -> True and * -> False"

    result = in_op.follow("abc", "" + NextToken)
    assert str(result) == "{abc} -> True and * -> False"

    result = in_op.follow("ade", "def" + NextToken)
    assert str(result) == "{ade} -> True and * -> False"

run_all_tests(globals())