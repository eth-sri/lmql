import lmql
from lmql.graphs.merging import *

from random import random, seed

seed(43)

@lmql.query
def cot(question):
    '''lmql
    sample


    return "cot success"
    '''

@lmql.query
def cot_superhard(question):
    '''lmql
    sample

    # if random() < 0.5:
    #     assert False, "This is a super hard question, I don't know how to answer it."
    
    return "success"
    '''

@lmql.query
def cot_hard(question):
    '''lmql
    return cot(question) | cot_superhard(question)
    '''

@lmql.query
def cot_answer(question): 
    '''lmql
    reasoning = cot_hard(question)
    print("reasoning", type(reasoning), [reasoning])

    return "89 answer with " + reasoning
    '''

@lmql.query(decoder='sample')
def ao_answer(question):
    '''lmql
    return "AO answer 12"
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
                   parallel=1)
        print(lmql.certificate(t).asdict().get("metrics"))
    # to inspect the resulting graph, run 
    # lmql graph-watch graph.json 
    # and open http://localhost:1234 in your browser