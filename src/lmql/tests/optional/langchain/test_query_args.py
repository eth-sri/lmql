import lmql
from lmql.tests.expr_test_utils import run_all_tests

# multi kw default
@lmql.query
async def multi_kw_chain(s: str = 'default', a: int = 12):
    '''lmql
    argmax
        return {"result": (s, a)}
    from
        "chatgpt"
    '''

# multi kw default
@lmql.query
async def no_return_chain(s: str = 'default', a: int = 12):
    '''lmql
    argmax
        "This is [R1] and [R2]"
    from
        "chatgpt"
    where
        R1 == s and R2 == "8"
    '''

def test_decorated_chain():
    c = multi_kw_chain.aschain(output_keys=["result"])
    
    input_value = "Hi there"
    a_value = 8

    # as chain
    s,a = c({"s": input_value, "a": a_value})["result"]
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == a_value, f"Expected {a_value}, got {a}"

    c = no_return_chain.aschain()
    res = c({"s": input_value, "a": a_value})
    s = res["R1"]
    a = res["R2"]
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == str(a_value), f"Expected {a_value}, got {a}"

multipos_chain = lmql.query('''lmql
argmax
    return {"result": (s, a)}
from
    "chatgpt"
'''
, input_variables=['s', 'a']).aschain(output_keys=['result'])

def test_query_args_with_str_aschain():
    input_value = "Hi there"
    a_value = 8

    # as chain
    s,a = multipos_chain({"s": input_value, "a": a_value})["result"]
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == a_value, f"Expected {a_value}, got {a}"

if __name__ == "__main__":
    run_all_tests(globals())