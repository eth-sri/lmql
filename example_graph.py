import lmql
from lmql.graphs.merging import *

@lmql.query
def cot(question):
    '''lmql
    "Q: {question} A: Let's think step by step (one sentences). [REASONING]" where len(TOKENS(REASONING)) < 20
    return REASONING
    '''

@lmql.query
def cot_answer(question) -> int: 
    '''lmql
    argmax(verbose=True)

    "Q: {question}\n A: {cot(question)} Thus the answer is[ANSWER]" where len(TOKENS(ANSWER)) < 20
    return ANSWER
    '''

@lmql.query
def ao_answer(question) -> int:
    '''lmql
    sample(verbose=True)

    "Q: {question}\n A: The answer is[ANSWER]" where len(TOKENS(ANSWER)) < 20
    return ANSWER
    '''

@lmql.query(merge=ByValue())
def answer(question):
    '''lmql
    return ao_answer(question) | cot_answer(question)
    '''

if __name__ == "__main__":
    # graph query
    lmql.infer(answer, question="What is 23*2-123?", state="graph.json", iterations=4)
    # to inspect the resulting graph, run 
    # lmql graph-watch graph.json 
    # and open http://localhost:1234 in your browser