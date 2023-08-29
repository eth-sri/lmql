import lmql
from expr_test_utils import run_all_tests

@lmql.query(model=lmql.model("random", seed=123))
def test_noprompt():
    '''lmql
    "[RESPONSE]" where len(TOKENS(RESPONSE)) < 10
    assert RESPONSE == " strides nutssa fallout Augustine frog malnutrition teasing", f"Expected fixed random value but got {[RESPONSE]}"
    '''

@lmql.query(model=lmql.model("random", seed=123))
async def noprompt_beam():
    '''lmql
    beam(n=2)
    "[RESPONSE]" where len(TOKENS(RESPONSE)) < 10
    '''

async def test_noprompt_beam():
    rs = await noprompt_beam()
    assert [r.variables['RESPONSE'] for r in rs] == [' strides stridesSepSep', ' strides stridesSepSep unidentified'], f"Expected fixed random value but got {[r.variables['RESPONSE'] for r in rs]}"

@lmql.query(model="openai/text-ada-001")
def test_noprompt_openai():
    '''lmql
    "[RESPONSE]" where len(TOKENS(RESPONSE)) < 10
    expected = "\n\nThe first step in any software development"
    assert RESPONSE == "\n\nThe first step in any software development", f"Expected '{expected}' got {[RESPONSE]}"
    '''

@lmql.query(model=lmql.model("random", seed=123))
def test_noprompt_with_constraints():
    '''lmql
    "[RESPONSE]" where RESPONSE in ["YES", "NO"]
    assert RESPONSE == "YES", f"Expected 'YES' got {[RESPONSE]}"
    '''

@lmql.query
def nested_query():
    '''lmql
    "[RESPONSE]" where RESPONSE in ["YES", "NO"]
    return RESPONSE
    '''

@lmql.query(model=lmql.model("random", seed=123))
def test_noprompt_with_nested_query():
    '''lmql
    "[RESPONSE: nested_query]"
    assert RESPONSE == "YES", f"Expected 'YES' got {[RESPONSE]}"
    '''

@lmql.query
def nested_static(value):
    '''lmql
    if value == 'a': return "YES"
    else: return "NO"
    '''

@lmql.query(model=lmql.model("random", seed=123))
def test_noprompt_with_nested_static_query():
    '''lmql
    "[RESPONSE: nested_static('a')]"
    assert RESPONSE == "YES", f"Expected 'YES' got {[RESPONSE]}"
    '''

if __name__ == "__main__":
    run_all_tests(globals())