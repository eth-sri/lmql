import lmql

CONSTANT = 1


noinput = lmql.query('''lmql
argmax
    return (s,)
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

async def test_lmql_run_args():
    input_value = "Hi there"
    a_value = 8 

    query = '''lmql
argmax
    return s
from
    "chatgpt"
'''

    try:
        s = (await lmql.run(query))[0]
        assert False, f"Expected error, got {s}"
    except TypeError as e:
        assert "Failed to resolve variable 's'" in str(e), f"Expected error, got {e}"

    # no input but kw specified
    s = (await lmql.run(query, s=input_value))[0]
    assert s == input_value, f"Expected {input_value}, got {s}"

    multiquery = '''lmql
argmax
    return s, a
from
    "chatgpt"
'''

    # multikw
    s, a = (await lmql.run(multiquery, s=input_value, a=a_value))[0]
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == a_value, f"Expected {a_value}, got {a}"
