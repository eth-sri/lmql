import lmql
import numpy as np

from lmql.tests.expr_test_utils import run_all_tests

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