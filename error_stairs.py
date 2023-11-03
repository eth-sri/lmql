import lmql
from lmql.graphs.merging import *

from random import random, seed

seed(43)

failed = {}

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
    
    if not "cot_superhard" in failed:
        failed["cot_superhard"] = 0
        assert False, "fail cot_superhard"

    return "super hard"@0.1
    '''

@lmql.query
def cot_hard(question):
    '''lmql
    if not "cot_hard" in failed:
        failed["cot_hard"] = 0
        assert False, "fail cot_hard"
    
    r = cot_superhard(question)

    return r
    '''

@lmql.query
def cot_answer(question): 
    '''lmql
    if not "cot_answer" in failed:
        failed["cot_answer"] = 0
        assert False, "fail cot_answer"
    
    reasoning = cot_hard(question)

    return ("answer to " + reasoning)@*0.5
    '''


@lmql.query
def answer(question):
    '''lmql
    if not "answer" in failed:
        failed["answer"] = 0
        assert False, "fail answer"

    return cot_answer(question)
    '''

@lmql.query(merge=ByIntValue(score='mean'))
def final_answer(question):
    '''lmql
    return answer(question)
    '''

def num_samples():
    import sys
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except:
            return 2
    return 2

if __name__ == "__main__":
    # graph query
    with lmql.traced("infer") as t:
        lmql.infer(final_answer, 
                   question="What is 23*2-123?", 
                   state="graph.json", 
                   samples=num_samples(),
                   parallel=1)
        print(lmql.certificate(t).asdict().get("metrics"))
    # to inspect the resulting graph, run 
    # lmql graph-watch graph.json 
    # and open http://localhost:1234 in your browser