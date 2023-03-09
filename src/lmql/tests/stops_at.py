from typing import List

from lmql.tests.expr_test_utils import *
from lmql.ops.ops import StopAtOp, NextToken

# enable_show_transformed()

# @lmql_test
# def test_stops_at():
#     expr = LMQLExpr(STOPS_AT(SEQ, "abc here"))
    
#     result = expr.digest("abc here we go abc here")
#     assert tuple(result) == (var(True), fin(False), var(True), var(True), var(True), fin(False))

# @lmql_test
# def test_stops_at2():
#     expr = LMQLExpr(STOPS_AT(SEQ, "abc her"))
    
#     result = expr.digest("abc here we go abc here")
#     assert tuple(result) == (var(True), fin(False), var(True), var(True), var(True), fin(False))

@lmql_test
def test_stops_at1_follow():
    expr = LMQLExpr(STOPS_AT(SEQ, "abc her"))
    
    follow = tuple(expr.follow("abc here we go"))
    assert str(follow) == "(* -> var(True), {eos} -> var(True) and * -> fin(False), * -> var(True), * -> var(True))"

@lmql_test
def test_stops_at2_follow():
    expr = LMQLExpr(STOPS_AT(SEQ, "abc her"))
    
    follow = tuple(expr.follow("abc here we go abc here"))
    assert str(follow) == "(* -> var(True), {eos} -> var(True) and * -> fin(False), * -> var(True), * -> var(True), * -> var(True), {eos} -> var(True) and * -> fin(False))"

run_all_tests(globals())