import lmql
from lmql.tests.expr_test_utils import run_all_tests

def test_or():
    @lmql.query
    async def q():
        '''lmql
        sample(temperature=0.8, openai_chunksize=30, max_len=128)
            "The movie review in positive sentiment is: '[OUTPUT]"
        FROM
            "openai/text-ada-001"
        WHERE
            len(TOKENS(OUTPUT)) < 20 or len(TOKENS(OUTPUT)) < 30
        '''
    result = lmql.main(q)[0]

run_all_tests(globals())