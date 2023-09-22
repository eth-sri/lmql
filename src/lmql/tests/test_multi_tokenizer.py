"""
Tests mixing different tokenizers/models in the same LMQL process.
"""

import lmql
from lmql.tests.expr_test_utils import run_all_tests

RANDOM_GPT_OUTPUT = "safillardDean Service"
RANDOM_LLAMA_OUTPUT = " był Organ quella Running"

@lmql.query(model=lmql.model("random", vocab="gpt2", seed=1))
async def test_random_gpt():
    '''lmql
    "Hello[WORLD]" where len(TOKENS(WORLD)) == 4
    assert WORLD == RANDOM_GPT_OUTPUT
    return WORLD
    '''

@lmql.query(model=lmql.model("random", vocab="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded", seed=1))
async def test_random_llama():
    '''lmql
    "Hello[WORLD]" where len(TOKENS(WORLD)) == 4
    assert WORLD == RANDOM_LLAMA_OUTPUT
    return WORLD
    '''

@lmql.query(model=lmql.model("random", vocab="gpt2", seed=1))
async def test_llama_from_gpt():
    '''lmql
    "Hello[WORLD]" where len(TOKENS(WORLD)) == 4
    assert [WORLD, test_random_llama()] == [
        RANDOM_GPT_OUTPUT,
        RANDOM_LLAMA_OUTPUT
    ]
    '''

@lmql.query(model="chatgpt")
async def cg():
    '''lmql
    "Hello[WORLD]" where len(TOKENS(WORLD)) < 4
    return WORLD
    '''

@lmql.query(model="openai/gpt-3.5-turbo-instruct")
async def test_gpt35():
    '''lmql
    "Hello[WORLD]" where len(TOKENS(WORLD)) == 4
    r = [WORLD, cg()]
    assert r == [", I am a", "  Hello!"], "Expected {}, got {}".format(
        [", I am a", "Hello!"],
        r
    )
    return WORLD
    '''

if __name__ == "__main__":
    run_all_tests(globals())