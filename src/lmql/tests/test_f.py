import lmql
import lmql.algorithms as la

from lmql.tests.expr_test_utils import run_all_tests

def test_f_functions():
    a = lmql.F("Summarize this text: {text}: [SUMMARY]", "len(TOKENS(SUMMARY)) < 10", model=lmql.model("random", seed=123))
    assert type(a(text="This is a test.")) is str

def test_f_positional_args():
    a = lmql.F("Summarize this text: {text}: [SUMMARY]", "len(TOKENS(SUMMARY)) < 10", model=lmql.model("random", seed=123))
    assert type(a("This is a test.")) is str

def test_f_multiple_positional_args():
    a = lmql.F("Summarize this text: {text1}{text2}: [SUMMARY]", "len(TOKENS(SUMMARY)) < 10", model=lmql.model("random", seed=123))
    b = lmql.F("Summarize this text: {text}: [SUMMARY]", "len(TOKENS(SUMMARY)) < 10", model=lmql.model("random", seed=123))
    r1 = type(a("This is ", "a test."))
    r2 = type(b("This is a test."))
    
    assert r1 is str, "output should be a string"
    assert r1 == r2, "using positional and keyword args should result in the same output"
    

async def test_async_f_functions():
    a = lmql.F("Summarize this text: {text}: [SUMMARY]", "len(TOKENS(SUMMARY)) < 10", model=lmql.model("random", seed=123), is_async=True)
    assert type(await a(text="This is a test.")) is str

async def test_map_async_f_functions():
    # a = lmql.F("Summarize this text: {text}: [SUMMARY]", "len(TOKENS(SUMMARY)) < 10", model=lmql.model("random", seed=123), is_async=True)
    data = [
        "A dog walks into a bar.",
        "A cat goes for a walk.",
    ]
    q = lmql.F("Summarize this text: {text}: [SUMMARY]", "len(TOKENS(SUMMARY)) < 10", model=lmql.model("random", seed=123), is_async=True)
    r = await la.map(q, data)
    assert len(r) == 2

    r = await la.map("Summarize this text: {text}: [SUMMARY]", data, where="len(TOKENS(SUMMARY)) < 10", model=lmql.model("random", seed=123))
    assert len(r) == 2

def test_run_pos_args():
    source = '''lmql
    "Summarize this text: {t1}{t2}: [SUMMARY]" where len(TOKENS(SUMMARY)) < 4
    return SUMMARY
    '''

    r1 = lmql.run_sync(source, "This is ", "a test.", model=lmql.model("random", seed=123))
    r2 = lmql.run_sync(source, t1="This is ", t2="a test.", model=lmql.model("random", seed=123))
    
    assert r1 == r2, "using positional and keyword args should result in the same output"

if __name__ == "__main__":
    run_all_tests(globals())