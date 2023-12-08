"""
Tests mixing different tokenizers/models in the same LMQL process.
"""

import lmql
from lmql.tests.expr_test_utils import run_all_tests

@lmql.query(model="chatgpt")
async def cg():
    '''lmql
    "Hello[WORLD]" where len(TOKENS(WORLD)) < 3
    return WORLD
    '''

@lmql.query(model="openai/gpt-3.5-turbo-instruct")
async def test_gpt35():
    '''lmql
    "Hello[WORLD]" where len(TOKENS(WORLD)) == 4
    r = [WORLD, cg()]
    assert r == [", I am a", " Hello!"], "Expected {}, got {}".format(
        [", I am a", " Hello!"],
        r
    )
    return WORLD
    '''

if __name__ == "__main__":
    run_all_tests(globals())