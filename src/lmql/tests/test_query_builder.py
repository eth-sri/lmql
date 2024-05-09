import lmql
import numpy as np

from lmql.tests.expr_test_utils import run_all_tests



def test_query_builder():
    # Example usage:
    query = (lmql.QueryBuilder()
              .set_decoder('argmax')
              .set_prompt('What is the capital of France? [ANSWER]')
              .set_model('local:gpt2')
              .set_where('len(TOKENS(ANSWER)) < 10')
              .set_where('len(TOKENS(ANSWER)) > 2')
              .build())

    expected = 'argmax "What is the capital of France? [ANSWER]" from "local:gpt2" where len(TOKENS(ANSWER)) < 10 and len(TOKENS(ANSWER)) > 2'

    assert expected==query.query_string, f"Expected: {expected}, got: {query.query_string}"
    out = query.run_sync()

def test_query_builder_with_dist():

    query = (lmql.QueryBuilder()
              .set_decoder('argmax')
              .set_prompt('What is the capital of France? [ANSWER]')
              .set_model('local:gpt2')
              .set_distribution('ANSWER', '["Paris", "London"]')
              .build())

    expected = 'argmax "What is the capital of France? [ANSWER]" from "local:gpt2" distribution ANSWER in ["Paris", "London"]'

    assert expected==query.query_string, f"Expected: {expected}, got: {query.query_string}"
    out = query.run_sync()

if __name__ == "__main__":
    run_all_tests(globals())