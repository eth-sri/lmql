import lmql

query = '''lmql
argmax
    return s
from
    "chatgpt"
'''
s_value = "hi there"

def test_sync_run():
    s, = lmql.run_sync(query, s=s_value)
    assert s == s_value, f"Expected {s_value}, got {s}"

    @lmql.query
    def sync_query(s: str):
        '''lmql
        argmax
            return s
        from
            "chatgpt"
        '''
    
    s, = sync_query(s=s_value)
    assert s == s_value, f"Expected {s_value}, got {s}"

async def test_async_run():
    # run async
    s, = await lmql.run(query, s=s_value)
    assert s == s_value, f"Expected {s_value}, got {s}"

    query_fails = '''lmql
argmax
    assert False, "This should not be run"
    return s
from
    "chatgpt"
'''

    try:
        s, = lmql.run_sync(query_fails, s=s_value)
        assert False, "Expected an exception when running lmql.run_sync in an async context"
    except Exception as e:
        assert "LMQL queries cannot be called synchronously from within an async context" in str(e), f"Expected an exception when running lmql.run_sync in an async context, got {e}"