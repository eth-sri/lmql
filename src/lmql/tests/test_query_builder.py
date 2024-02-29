import lmql
import numpy as np

from lmql.tests.expr_test_utils import run_all_tests

from lmql.language.query_builder import QueryBuilder


def test_query_builder():
    # Example usage:
    prompt = (QueryBuilder()
              .set_decoder('argmax')
              .set_prompt('What is the capital of France? [ANSWER]')
              .set_model('gpt2')
              .set_where('len(TOKENS(ANSWER)) < 10')
              .set_where('len(TOKENS(ANSWER)) > 2')
              .build())

    expected = 'argmax "What is the capital of France? [ANSWER]" from "gpt2" where len(TOKENS(ANSWER)) < 10 and len(TOKENS(ANSWER)) > 2'

    assert expected==prompt, f"Expected: {expected}, got: {prompt}"
    out = lmql.run_sync(prompt,)

def test_query_builder_with_dist():

    prompt = (QueryBuilder()
              .set_decoder('argmax')
              .set_prompt('What is the capital of France? [ANSWER]')
              .set_model('gpt2')
              .set_distribution('ANSWER', '["Paris", "London"]')
              .build())

    expected = 'argmax "What is the capital of France? [ANSWER]" from "gpt2" distribution ANSWER in ["Paris", "London"]'

    assert expected==prompt, f"Expected: {expected}, got: {prompt}"
    out = lmql.run_sync(prompt,)

if __name__ == "__main__":
    run_all_tests(globals())