import lmql
from lmql.graphs.merging import *

@lmql.query
def cot(question):
    '''lmql
    sample
    
    "Q: {question} A: Let's think step by step (one sentences). [REASONING]"

    return REASONING@logprobs(REASONING).mean()
    '''

@lmql.query
def cot_answer(question): 
    '''lmql
    reasoning = cot(question)
    "Q: {question}\n A:{reasoning} Thus the answer is[ANSWER]" where len(TOKENS(ANSWER)) < 20

    return ANSWER@(logprobs(ANSWER).mean() + score(reasoning))
    '''

@lmql.query(decoder='sample')
def ao_answer(question):
    '''lmql
    "Q: {question}\n A: The answer is[ANSWER]" where len(TOKENS(ANSWER)) < 20
    return ANSWER@(logprobs(ANSWER).mean())
    '''

@lmql.query(merge=ByIntValue(score='mean'))
def answer(question):
    '''lmql
    return ao_answer(question) | cot_answer(question)
    '''

if __name__ == "__main__":
    # graph query
    lmql.infer(answer, question="What is 23*2-123?", state="graph.json", samples=4)
    # to inspect the resulting graph, run 
    # lmql graph-watch graph.json 
    # and open http://localhost:1234 in your browser