import lmql
from lmql.tests.expr_test_utils import run_all_tests

async def test_eq_str():
    @lmql.query
    async def q():
        '''lmql
        argmax
            "Q: Hi. A:[OUTPUT]"
        FROM
            "openai/text-davinci-003"
        WHERE
            OUTPUT == "Hello you"
        '''
    result = await q()
    assert result[0].variables["OUTPUT"] == "Hello you"


async def test_double_eq_str():
    @lmql.query
    async def q():
        '''lmql
        argmax
            "Q: Hi. A:[OUTPUT]"
        FROM
            "openai/text-davinci-003"
        WHERE
            OUTPUT == "Hello you" or OUTPUT == "Hello There"
        '''
    result = await q()
    assert result[0].variables["OUTPUT"] in ["Hello you", "Hello There"]


async def test_double_eq_int():
    @lmql.query
    async def q():
        '''lmql
        argmax
            "Q: Hi. A:[OUTPUT]"
        FROM
            "openai/text-davinci-003"
        WHERE
            len(TOKENS(OUTPUT)) == 2
        '''
    result = await q()
    assert result[0].prompt == "Q: Hi. A: Hi."

async def test_double_eq_charlen():
    @lmql.query
    async def q():
        '''lmql
        argmax
            "Q: Hi. A:[OUTPUT]"
        FROM
            "openai/text-davinci-003"
        WHERE
            len(OUTPUT) == 2
        '''
    result = await q()
    assert result[0].prompt == "Q: Hi. A:\n\n"

@lmql.query
async def test_later_var_token_constrained():
    '''lmql
    argmax(max_len=256)
        "A rhyme:\n"
        "Verse: [RHYME_START]\n"
        for i in range(5):
            "Verse: [RHYME]\n"
            assert RHYME == "\n\nI'm not"
    from
        'openai/text-ada-001'
    where
        len(TOKENS(RHYME)) == 5 and len(TOKENS(RHYME_START)) == 5
    '''

@lmql.query
async def test_stops_before_exact_token_len():
    '''lmql
    argmax(max_len=256, openai_chunksize=4)
        "A rhyme named '[NAME]':\n"
        assert not "'" in NAME
        "Verse: [RHYME]\n"
        assert RHYME == "\n\nAin"
        "Verse: [RHYME]\n"
        assert RHYME == "\n\nAll\n"
        "Verse: [RHYME]\n"
        assert RHYME == "\n\nAll\n"
        "Verse: [RHYME]\n"
        assert RHYME == "\n\nAll\n"
        "Verse: [RHYME]\n"
        assert RHYME == "\n\nAll\n"
    from
        'openai/text-ada-001'
    where
        len(TOKENS(RHYME)) == 4 and STOPS_BEFORE(NAME, "'")
    '''

run_all_tests(globals())