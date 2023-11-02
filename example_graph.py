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
def cot_superhard(question):
    '''lmql
    sample
    
    "Q: {question} A: Let's think precisely:\n[REASONING]"

    return REASONING@logprobs(REASONING).mean()
    '''

@lmql.query
def cot_medium_hard(question):
    '''lmql
    sample

    "Q: {question} A: Let's think step by step with a dashed list:\n[REASONING]"

    return REASONING@logprobs(REASONING).mean()
    '''

@lmql.query
def cot_hard(question):
    '''lmql
    return cot_superhard(question) | cot_medium_hard(question)
    '''

@lmql.query
def cot_answer(question): 
    '''lmql
    reasoning = cot(question) | cot_hard(question)
    "Q: {question}\n A:{reasoning} Thus the answer is[ANSWER]" where len(TOKENS(ANSWER)) < 20

    return ANSWER@(logprobs(ANSWER).mean() + score(reasoning))
    '''

@lmql.query(decoder='sample')
def ao_answer(question):
    '''lmql
    "Q: {question}\n A: The answer is[ANSWER]" where len(TOKENS(ANSWER)) < 20
    return ANSWER@(logprobs(ANSWER).mean())
    '''

@lmql.query
def answer(question):
    '''lmql
    return ao_answer(question) | cot_answer(question)
    '''

@lmql.query(merge=ByIntValue(score='mean'))
def final_answer(question):
    '''lmql
    return answer(question)
    '''

if __name__ == "__main__":
    # graph query
    with lmql.traced("infer") as t:
        lmql.infer(final_answer, 
                   question="What is 23*2-123?", 
                   state="graph.json", 
                   samples=10,
                   parallel=1)
        print(lmql.certificate(t).asdict().get("metrics"))
    # to inspect the resulting graph, run 
    # lmql graph-watch graph.json 
    # and open http://localhost:1234 in your browser