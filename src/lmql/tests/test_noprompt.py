import lmql
from expr_test_utils import run_all_tests

t = lmql.tokenizer("gpt2")

def token_diff(s1, s2):
    ids1 = t(s1)["input_ids"]
    ids2 = t(s2)["input_ids"]
    return ids2[len(ids1):]

@lmql.query(model=lmql.model("random", seed=123))
def test_noprompt():
    '''lmql
    "[RESPONSE]" where len(TOKENS(RESPONSE)) < 10
    assert RESPONSE == " Protocol radi programmes Lump Zerg garg Cann troopsantasy", f"Expected fixed random value but got {[RESPONSE]}"
    '''

@lmql.query(model=lmql.model("random", seed=123))
async def noprompt_beam():
    '''lmql
    beam(n=2)
    "[RESPONSE]" where len(TOKENS(RESPONSE)) < 10
    '''

async def test_noprompt_beam():
    rs = await noprompt_beam()
    assert [r.variables['RESPONSE'] for r in rs] == [' Protocol', ' Protocol radi'], f"Expected fixed random value but got {[r.variables['RESPONSE'] for r in rs]}"

@lmql.query(model=lmql.model("random", seed=123))
def test_noprompt_with_constraints():
    '''lmql
    "[RESPONSE]" where RESPONSE in ["YES", "NO"]
    assert RESPONSE == "NO", f"Expected 'NO' got {[RESPONSE]}"
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
    assert RESPONSE == "NO", f"Expected 'YES' got {[RESPONSE]}"
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