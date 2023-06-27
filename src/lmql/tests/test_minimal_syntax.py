import lmql
from lmql.tests.expr_test_utils import run_all_tests

@lmql.query
def test_hello_full():
    '''lmql
    argmax 
        "Say 'this is a test':[RESPONSE]" 
    from 
        lmql.model("random", seed=123)
    where 
        len(TOKENS(RESPONSE)) < 10
    '''

@lmql.query(decoder="argmax", model=lmql.model("random", seed=123))
def test_hello_minimal():
    '''lmql
    "Say 'this is a test':[RESPONSE]" where len(TOKENS(RESPONSE)) < 10
    '''

test_hello_string_query = lmql.query("'Say \"this is a test\":[RESPONSE]' where len(TOKENS(RESPONSE)) < 10", 
                                     model=lmql.model("random", seed=123))

test_hello_oneline = lmql.F("Say 'this is a test': [RESPONSE]", "len(TOKENS(RESPONSE)) < 10", model="random")

# test_davinci_says_it = lmql.F("Say 'this is a test': [RESPONSE]", model="openai/text-davinci-003")


@lmql.query(decoder="sample", temperature=1.2, model=lmql.model("random", seed=123))
def test_joke():
    '''lmql
    """A list of good dad jokes. A indicates the punchline
    Q: How does a penguin build its house?
    A: Igloos it together.
    Q: Which knight invented King Arthur's Round Table?
    A: Sir Cumference."""
    "Q:[JOKE]\n" where len(JOKE) < 120 and len(TOKENS(JOKE)) < 20 and STOPS_AT(JOKE, "?")
    "A:[PUNCHLINE]" where STOPS_AT(PUNCHLINE, "\n") and len(TOKENS(PUNCHLINE)) < 20 and len(PUNCHLINE) > 1
    '''

if __name__ == "__main__":
    run_all_tests(globals())