from lmql.tests.expr_test_utils import *

# enable_show_transformed()

@lmql_test
def test_stops_at():
    expr = LMQLExpr(STARTS_WITH(SEQ, ["___ _"]))
    
    result = tuple(expr.digest("abc here we go"))
    assert result == (fin(False), fin(False), fin(False), fin(False))

    result = tuple(expr.digest("___ _ abc"))
    assert result == (var(False), fin(True), fin(True))

    follow = expr.follow("___ abc here we go")
    assert str(next(follow)) == "{ _} -> fin(True) and * \ { _} -> fin(False)"
    assert str(next(follow)) == "* -> fin(False)"
    assert str(next(follow)) == "* -> fin(False)"
    assert str(next(follow)) == "* -> fin(False)"

    follow = expr.follow("___ _ abc here we go")
    # print(tuple(follow))
    assert str(next(follow)) == "{ _} -> fin(True) and * \ { _} -> fin(False)"
    assert str(next(follow)) == "* -> fin(True)"
    assert str(next(follow)) == "* -> fin(True)"
    assert str(next(follow)) == "* -> fin(True)"

run_all_tests(globals())