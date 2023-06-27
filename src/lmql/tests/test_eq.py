import lmql
from lmql.tests.expr_test_utils import run_all_tests
from lmql.runtime.tokenizer import load_tokenizer

t = load_tokenizer("gpt2")

def token_diff(s1, s2):
    ids1 = t(s1)["input_ids"]
    ids2 = t(s2)["input_ids"]
    return ids2[len(ids1):]

def tlen(s):
    return len(t(s)["input_ids"])

async def test_eq_str():
    @lmql.query
    async def q():
        '''lmql
        argmax
            "Q: Hi. A:[OUTPUT]"
        FROM
            lmql.model("random", seed=123)
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
            lmql.model("random", seed=123)
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
            lmql.model("random", seed=123)
        WHERE
            len(TOKENS(OUTPUT)) == 2
        '''
    result = await q()
    ids = token_diff("Q: Hi. A:", result[0].prompt)
    assert len(ids) == 2

async def test_double_eq_charlen():
    @lmql.query
    async def q():
        '''lmql
        argmax
            "Q: Hi. A:[OUTPUT]"
        from
            lmql.model("random", seed=123)
        where
            len(OUTPUT) == 2
        '''
    result = await q()
    assert len(result[0].variables["OUTPUT"]) == 2

@lmql.query
async def test_later_var_token_constrained():
    '''lmql
    argmax(max_len=256)
        "A rhyme:\n"
        "Verse: [RHYME_START]\n"
        for i in range(5):
            "Verse: [RHYME]\n"
            assert len(t(RHYME)["input_ids"]) == 5, "RHYME has " + str(len(t(RHYME)["input_ids"])) + " tokens"
    from
        lmql.model("random", seed=123)
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
        assert tlen(RHYME) == 4
        "Verse: [RHYME]\n"
        assert tlen(RHYME) == 4
        "Verse: [RHYME]\n"
        assert tlen(RHYME) == 4
        "Verse: [RHYME]\n"
        assert tlen(RHYME) == 4
        "Verse: [RHYME]\n"
        assert tlen(RHYME) == 4
    from
        lmql.model("random", seed=123)
    where
        len(TOKENS(RHYME)) == 4 and STOPS_BEFORE(NAME, "'")
    '''

if __name__ == "__main__":
    run_all_tests(globals())