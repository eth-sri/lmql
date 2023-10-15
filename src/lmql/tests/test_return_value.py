import lmql
from lmql.tests.expr_test_utils import run_all_tests

@lmql.query(model="random", seed=123)
def none_return_value():
    '''lmql
    "Hi, [COMPLETION]." where len(TOKENS(COMPLETION)) == 2
    return None
    return "Something"
    '''

@lmql.query(model="random", seed=123)
def some_return_value():
    '''lmql
    "Hi, [COMPLETION]." where len(TOKENS(COMPLETION)) == 2
    return "Something"
    '''

def test_return_value():
    a = none_return_value()
    assert a is None, "Expected return value to be None but got {a}"

def test_return_value_sample_2():
    a = none_return_value(decoder="beam", n=2)

    assert len(a) == 2, f"Expected return value to be a list of length 2 but got {len(a)}"
    assert a[0] is None, f"Expected return value to be None but got {a[0]}"
    assert a[1] is None, f"Expected return value to be None but got {a[1]}"

def test_some_return_value():
    a = some_return_value()
    assert a == "Something", f"Expected return value to be 'Something' but got {a}"

@lmql.query(model="random", seed=123)
def nested_none():
    '''lmql
    "[TEST: none_return_value]."
    return context.prompt
    '''

def test_nested_none():
    a = nested_none()
    assert a == "None.", f"Expected return value to be 'None.' but got '{a}'"

@lmql.query(model="random", seed=123)
def nested_some():
    '''lmql
    "[TEST: some_return_value]."
    return context.prompt
    '''

def test_nested_some():
    a = nested_some()
    assert a == "Something.", f"Expected return value to be 'Something.' but got '{a}'"

@lmql.query(model="random", seed=123)
def nested_no_return():
    '''lmql
    "Hi,[COMPLETION]" where len(TOKENS(COMPLETION)) == 2
    '''

# now use in query
@lmql.query(model="random", seed=123)
def nested_no_return_in_query():
    '''lmql
    "[TEST: nested_no_return]."
    return context.prompt
    '''

def test_nested_no_return_in_query():
    a = nested_no_return_in_query()
    assert a == "Hi,efullypresent.", f"Expected return value to be 'None.' but got '{a}'"

def test_no_return_in_query():
    a = nested_no_return()
    # should give LMQLResult
    assert type(a) is lmql.LMQLResult, f"Expected return value to be 'LMQLResult' but got '{type(a)}'"

def test_no_return_in_query_sample_2():
    a = nested_no_return(decoder="sample", n=2)
    # should give LMQLResult
    assert len(a) == 2, f"Expected return value to be a list of 'LMQLResult' but got '{type(a)}'"
    assert type(a[0]) is lmql.LMQLResult, f"Expected return value to be 'LMQLResult' but got '{type(a)}'"
    assert type(a[1]) is lmql.LMQLResult, f"Expected return value to be 'LMQLResult' but got '{type(a)}'"

@lmql.query
def two_path_return(a:int):
    '''lmql
    if a > 0:
        return None
    elif a == 0:
        return
    else:
        return "Something"
    
    return "Never"
    '''

def test_two_path_return():
    a = two_path_return(1)
    assert a is None, f"Expected return value to be 'None' but got '{a}'"

    a = two_path_return(-1)
    assert a == "Something", f"Expected return value to be 'Something' but got '{a}'"

    a = two_path_return(0)
    assert type(a) is lmql.LMQLResult, f"Expected return value to be 'LMQLResult' but got '{type(a)}'"

    a = two_path_return(-1, decoder="sample", n=2)
    assert a == "Something", f"Expected return value to be 'Something' but got '{a}'"

@lmql.query
def early_return_with_nothing():
    '''lmql
    return
    return "Something"
    '''

def test_early_return_with_nothing():
    a = early_return_with_nothing()
    # should be LMQLResult not 'Something'
    assert type(a) is lmql.LMQLResult, f"Expected return value to be 'LMQLResult' but got '{type(a)}'"

@lmql.query
def early_conditionally_return_with_nothing(a: int):
    '''lmql
    if a > 0:
        return
    return "Something"
    '''

def test_early_conditionally_return_with_nothing():
    a = early_conditionally_return_with_nothing(1)
    # should be LMQLResult not 'Something'
    assert type(a) is lmql.LMQLResult, f"Expected return value to be 'LMQLResult' but got '{type(a)}'"

    a = early_conditionally_return_with_nothing(-1)
    assert a == "Something", f"Expected return value to be 'Something' but got '{a}'"

if __name__ == "__main__":
    run_all_tests(globals())