import lmql
from lmql.tests.expr_test_utils import run_all_tests

def test_stopping_overlap_before():
    @lmql.query
    async def q():
        '''lmql
        sample(temperature=0.8, max_len=64)
            "The movie review in positive sentiment is: [OUTPUT]"
        FROM
            "openai/text-ada-001"
        WHERE
            STOPS_BEFORE(OUTPUT, "\\n") and STOPS_BEFORE(OUTPUT, "n") and len(TOKENS(OUTPUT)) < 10
        '''
    result = lmql.main(q)[0]

run_all_tests(globals())