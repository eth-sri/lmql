import lmql
from lmql.tests.expr_test_utils import run_all_tests

async def test_stopping_overlap_before():
    @lmql.query
    async def q():
        '''lmql
        sample(temperature=0.8, max_len=64)
            "The movie review in positive sentiment is: [OUTPUT]"
        FROM
            "openai/text-ada-001"
        WHERE
            STOPS_BEFORE(OUTPUT, "\n") and STOPS_BEFORE(OUTPUT, "n") and len(TOKENS(OUTPUT)) < 10
        '''
    (await q())[0]

async def test_stopping_double_match():
    @lmql.query
    async def q():
        '''lmql
        argmax 
            '{{"1","2","3",[COMPL]}}'
        from 
            "openai/text-ada-001" 
        where 
            len(TOKENS(COMPL)) < 10 and STOPS_AT(COMPL, '"')
        '''
    assert (await q())[0].variables["COMPL"] == '4"'

async def test_stopping_double_match_before():
    @lmql.query
    async def q():
        '''lmql
        argmax 
            '{{"1","2","3",[COMPL]"}}'
        from 
            "openai/text-ada-001" 
        where 
            len(TOKENS(COMPL)) < 10 and STOPS_BEFORE(COMPL, '"')
        '''
    assert (await q())[0].variables["COMPL"] == '4'

async def test_stopping_single_match():
    @lmql.query
    async def q():
        '''lmql
        argmax 
            """
            My name is Peter. In JSON:
            {{
                "name": "[COMPL]
            }}
            """
        from 
            "openai/text-ada-001" 
        where 
            STOPS_AT(COMPL, '"')
        '''
    assert (await q())[0].variables["COMPL"] == 'Peter"'

@lmql.query
async def test_conditional_stopping():
    '''lmql
    argmax 
        "The movie review in positive sentiment is: [OUTPUT]"
        assert OUTPUT.count("The") == 2
    from 
        "openai/text-ada-001" 
    where 
        len(TOKENS(OUTPUT)) > 18 and STOPS_AT(OUTPUT, "The")
    '''

@lmql.query
async def test_conditional_or_stopping():
    '''lmql
    argmax 
        "The movie review in positive sentiment is: [OUTPUT]"
        assert OUTPUT.count("The") == 1
    from 
        "openai/text-ada-001" 
    where 
        len(TOKENS(OUTPUT)) > 20 or STOPS_AT(OUTPUT, "The")
    '''

@lmql.query
async def test_double_stop_rewrite():
    '''lmql
    argmax 
        "The movie review in positive sentiment is: [OUTPUT] Here"
        assert OUTPUT.endswith("The")
    from 
        "openai/text-ada-001" 
    where 
        STOPS_BEFORE(OUTPUT, " ") and STOPS_AT(OUTPUT, "re")
    '''

@lmql.query
async def test_double_stop_rewrite_space():
    '''lmql
    argmax 
        "The movie review in positive sentiment is: [OUTPUT] Here"
        assert OUTPUT.endswith(" ")
    from 
        "openai/text-ada-001" 
    where 
        STOPS_AT(OUTPUT, " ") and STOPS_AT(OUTPUT, "re")
    '''

@lmql.query
async def test_stop_should_not_postprocess_if_sc_not_satisfied():
    '''lmql
    argmax 
        "A good movie review:[REVIEW] "
        assert REVIEW.endswith("smiles"), "Expected REVIEW to end with 'smiles', but was " + str([REVIEW])
    from 
        lmql.model("random", seed=123)
    where
        len(TOKENS(REVIEW)) > 10 and STOPS_AT(REVIEW, "exempted") and STOPS_AT(REVIEW, "smiles")
    '''

@lmql.query
async def test_stop_before_should_not_postprocess_if_sc_not_satisfied():
    '''lmql
    argmax 
        "A good movie review:[REVIEW] "
        assert REVIEW.endswith("smiles"), "Expected REVIEW to end with 'smiles', but was " + str([REVIEW])
    from 
        lmql.model("random", seed=123)
    where
        len(TOKENS(REVIEW)) > 10 and STOPS_BEFORE(REVIEW, "exempted") and STOPS_AT(REVIEW, "smiles")
    '''

if __name__ == "__main__":
    run_all_tests(globals())