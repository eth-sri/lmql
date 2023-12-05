import lmql

CONSTANT = 1


noinput = lmql.query('''lmql
argmax
    return s
from
    "chatgpt"
'''
)

positional_only = lmql.query('''lmql
argmax
    return s
from
    "chatgpt"
'''
, input_variables=['s'])

multipos = lmql.query('''lmql
argmax
    return s, a
from
    "chatgpt"
'''
, input_variables=['s', 'a'])

async def test_query_args_with_str():
    input_value = "Hi there"
    a_value = 8 

    # no input with without input_variables
    try:
        s = (await noinput())
        assert False, f"Expected error, got {s}"
    except TypeError as e:
        assert "Failed to resolve variable 's'" in str(e), f"Expected error, got {e}"

    # no input with kwargs 
    s = (await noinput(s=input_value, output_writer=lmql.printing))
    assert s == input_value, f"Expected {input_value}, got {s}"

    # positional only
    s = (await positional_only(input_value))
    assert s == input_value, f"Expected {input_value}, got {s}"

    # specify as kw
    s = (await positional_only(s=input_value))
    assert s == input_value, f"Expected {input_value}, got {s}"

    # multipos
    s, a = (await multipos(input_value, a_value))
    assert s == input_value, f"Expected {input_value}, got {s}"

    # specify partly as kw
    s, a = (await multipos(input_value, a=a_value))
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == a_value, f"Expected {a_value}, got {a}"

    # specify fully as kw
    s, a = (await multipos(s=input_value, a=a_value))
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == a_value, f"Expected {a_value}, got {a}"