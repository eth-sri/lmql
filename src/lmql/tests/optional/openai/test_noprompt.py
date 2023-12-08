import lmql

from lmql.tests.expr_test_utils import run_all_tests

@lmql.query(model="openai/text-ada-001")
def test_noprompt_openai():
    '''lmql
    "[RESPONSE]" where len(TOKENS(RESPONSE)) < 10
    expected = "\n\nThe first step in any software development"
    assert RESPONSE == "\n\nThe first step in any software development", f"Expected '{expected}' got {[RESPONSE]}"
    '''

if __name__ == "__main__":
    run_all_tests(globals())