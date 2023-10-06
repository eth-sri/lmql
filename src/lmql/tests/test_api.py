import lmql
import numpy as np

from lmql.tests.expr_test_utils import run_all_tests

def test_generate_sync():
    lmql.set_default_model(lmql.model("random", seed=123))

    result = lmql.generate_sync("Test", max_tokens=10)
    assert type(result) is str and len(result) > 0

async def test_generate():
    lmql.set_default_model(lmql.model("random", seed=123))

    result = await lmql.generate("Test", max_tokens=10)
    assert type(result) is str and len(result) > 0

async def test_llm_generate():
    llm = lmql.model("random", seed=123)
    result = await llm.generate("Test", max_tokens=10)
    assert type(result) is str and len(result) > 0

async def test_llm_multi_generate():
    llm = lmql.model("random", seed=123)
    result = await llm.generate(["Test", "Test"], max_tokens=10, temperature=0.2, n=2)
    assert type(result) is list and len(result) == 2
    for r in result:
        assert type(r) is str and len(r) > 0

def test_score_sync():
    lmql.set_default_model(lmql.model("random", seed=123))

    result = lmql.score_sync("Test", "Test")
    
    assert type(result) is lmql.ScoringResult
    assert len(result.seqs) == 1
    assert len(result.token_scores) == 1 and result.token_scores[0].shape == (1,)
    assert len(result.full_token_scores) == 1 and np.array(result.full_token_scores[0]).shape == (2,)

    assert result.logprobs().shape == (1,)

def test_llm_score_two():
    lmql.set_default_model(lmql.model("random", seed=123))

    result = lmql.score_sync("Hello", ["World", "Test"])

    assert type(result) is lmql.ScoringResult
    assert len(result.seqs) == 2
    assert len(result.token_scores) == 2 and result.token_scores[0].shape == (1,)
    assert len(result.full_token_scores) == 2 and np.array(result.full_token_scores[0]).shape == (2,)

    assert result.argmax() in ["World", "Test"]

def test_llm_local():
    m = lmql.model("local:sshleifer/tiny-gpt2", silent=True)
    assert m.score_sync("Hello", ["World", "Test"]).argmax() == "Test"

def test_llm_openai():
    try:
        import lmql.runtime.openai_secret
    except:
        print("Skipping test_api.test_llm_openai because no OpenAI API configuration could be found.")
        return

    m = lmql.model("openai/text-davinci-003", silent=True)
    assert m.score_sync("Hello", ["World", "Test"]).argmax() == "World"

if __name__ == "__main__":
    run_all_tests(globals())