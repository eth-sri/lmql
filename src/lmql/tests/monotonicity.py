from lmql.tests.expr_test_utils import *

# enable_show_transformed()

@lmql_test
def test_var():
    expr = LMQLExpr(SEQ)
    result = expr.digest("How are you?".split(" "))

    assert next(result) == inc(("How",))

@lmql_test
def test_len():
    expr = LMQLExpr(len(SEQ))
    result = expr.digest("How are you?".split(" "))

    assert next(result) == inc(1)
    assert next(result) == inc(2)
    assert next(result) == inc(3)

@lmql_test
def test_lt():
    expr = LMQLExpr(len(SEQ) < 2)
    result = expr.digest("How are you?".split(" "))

    assert next(result) == var(True) # [How]
    assert next(result) == fin(False) # [How, are]
    assert next(result) == fin(False) # [How, are, you?]
    
    result = expr.digest("How are you?".split(" "))
    assert next(result) != fin(True) # [How]

@lmql_test
def test_gt():
    expr = LMQLExpr(len(SEQ))
    result = expr.digest("How are you?".split(" "))

    assert next(result) == var(False) # [How]
    assert next(result) == var(False) # [How, are]
    assert next(result) == fin(True) # [How, are, you?]

@lmql_test
def test_gt():
    expr = LMQLExpr(SELECT(SEQ, 1))
    result = expr.digest("How are you?".split(" "))

    assert next(result) == var(None)
    assert next(result) == fin("are")

@lmql_test
def test_len_constant():
    expr = LMQLExpr(len(SEQ) < var(3))
    result = expr.digest("How are you?".split(" "))

    assert next(result) == var(True)
    assert next(result) == var(True)
    assert next(result) == var(False)

@lmql_test
def test_len_gt():
    expr = LMQLExpr(len(SEQ) > 2)
    result = expr.digest("How are you?".split(" "))

    assert next(result) == var(False)
    assert next(result) == var(False)
    assert next(result) == fin(True)
    
@lmql_test
def test_gt_constant():
    expr = LMQLExpr(fin(4) > fin(3))
    result = tuple(expr.digest("How are you?".split(" ")))

    assert result == (fin(True), fin(True), fin(True))

@lmql_test
def test_lower_upper():
    expr = LMQLExpr(len(SEQ) > 2 and len(SEQ) < 5)
    result = tuple(expr.digest("one two three four five six seven".split(" ")))

    assert result == (var(False), var(False), var(True), var(True), fin(False), fin(False), fin(False))

@lmql_test
def test_lower_upper_empty():
    expr = LMQLExpr(len(SEQ) > 5 and len(SEQ) < 2)
    result = tuple(expr.digest("one two three four five six seven".split(" ")))

    assert result == (var(False), fin(False), fin(False), fin(False), fin(False), fin(False), fin(False))

@lmql_test
def test_lower_upper_hole():
    expr = LMQLExpr(len(SEQ) < 2 or len(SEQ) > 4)
    result = tuple(expr.digest("one two three four five six seven".split(" ")))

    # print(result) 
    assert result == (var(True), var(False), var(False), var(False), fin(True), fin(True), fin(True))

run_all_tests(globals())