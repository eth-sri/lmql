import lmql
from lmql.tests.expr_test_utils import run_all_tests

@lmql.query(model=lmql.model("random", seed=123))
def test_cot_fct():
    '''lmql
    @lmql.query
    def chain_of_thought():
        """lmql
        "A: Let's think step by step. [ANSWER]" where len(TOKENS(ANSWER)) < 4
        return ANSWER.strip()
        """

    "Q: It is August 12th, 2020. What date was it 100 days ago? [ANSWER: chain_of_thought]"
    assert ANSWER == "TrailsGaza 66", f"test_cot_fct: Expected fixed random value but got {[ANSWER]}"
    '''

@lmql.query(model=lmql.model("random", seed=123))
def test_no_return():
    '''lmql
    @lmql.query
    def items_list(n: int):
        """lmql
        for i in range(n):
            "-[ITEM]\n" where STOPS_AT(ITEM, "\n") and len(TOKENS(ITEM)) == 3
        """

    "A list of things not to forget to pack for your \
    next trip:\n[ITEMS: items_list(4)]"

    assert ITEMS == '-overty roof ISIS\n- seal sugars ones\n-hof catalyst freed\n- cmd adventuresonto\n', f"Expected fixed random value but got {[ITEMS]}"
    '''

@lmql.query
def dateformat():
    '''lmql
    "(respond in DD/MM/YYYY) [ANSWER]" where len(TOKENS(ANSWER)) == 4
    return ANSWER.strip()
    '''

@lmql.query(model=lmql.model("random", seed=123))
def test_multi_nested():
    '''lmql
    "Q: When was Obama born? [ANSWER: dateformat]\n"
    assert ANSWER == "amongst handshake chatting passenger", f"Expected fixed random value but got {[ANSWER]} for first question"
    "Q: When was Bruno Mars born? [ANSWER: dateformat]\n"
    assert ANSWER == "closely.」 tournament rollout", f"Expected fixed random value but got {[ANSWER]} for second question"
    "Q: When was Dua Lipa born? [ANSWER: dateformat]\n"
    assert ANSWER == "basedWidgetinst699", f"Expected fixed random value but got {[ANSWER]} for third question"

    "Out of these, who was born last?[LAST]" where len(TOKENS(LAST)) == 2
    assert LAST == "arel Hands", f"Expected fixed random value but got {[LAST]}"
    '''

@lmql.query
def one_of(choices: list):
    '''lmql
    "Among {choices}, what do you consider \
    most likely? [ANSWER]" where ANSWER in choices
    return ANSWER
    '''

@lmql.query(model=lmql.model("random", seed=123))
def test_one_of():
    '''lmql
    "Q: What is the capital of France? \
    [ANSWER: one_of(['Berlin', 'Paris', 'London'])]"
    assert ANSWER == "Paris", f"Expected fixed random value but got {[ANSWER]}"
    '''

@lmql.query
def cot_one_of(choices: list):
    '''lmql
    "A: Let's think step by step. [ANSWER: one_of(choices)]" where len(TOKENS(ANSWER)) < 4
    return ANSWER.strip()
    '''

@lmql.query
def test_double_tail_call():
    '''lmql
    "The answer is [ANSWER: cot_one_of(['Hello', 'Greetings'])]"
    '''

class NestedQueryMethods:
    def __init__(self):
        self.a = 12

    @lmql.query
    def chain_of_thought(self):
        '''lmql
        """A. Let's think step by step ({self.a}):
        [REASONING]
        Therefore the answer is[ANSWER]""" where STOPS_AT(ANSWER, ".") and len(TOKENS(ANSWER)) == 10 and len(TOKENS(REASONING)) == 10
        return ANSWER.strip() 
        '''

    @lmql.query(model=lmql.model("random", seed=124))
    def question(self):
        '''lmql
        """Q: Why is the sky blue?
        [ANSWER: self.chain_of_thought]"""
        return ANSWER.strip().rstrip(".").capitalize()
        '''

def test_nested_queries():
    q = NestedQueryMethods()
    r = q.question()
    assert r[0] == "Hi parrender 277 capit posteriorboston chuck神 heal", f"Expected fixed random value but got {r}"

if __name__ == "__main__":
    run_all_tests(globals())
 