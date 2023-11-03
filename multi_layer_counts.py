import lmql
from lmql.graphs.merging import *
from random import random, seed

class Count:
    def __init__(self, value):
        self.value = 0

    def __call__(self):
        self.value += 1
        return self.value

ctr = Count(0)
ctr2 = Count(0)

@lmql.query
def dep():
    '''lmql
    return 123
    '''

@lmql.query(decoder='sample')
def ao_answer(question):
    '''lmql
    a = dep()

    if ctr.value < 3:
        print("fail")
        ctr()
        assert False, "failed"
    
    ANSWER = str(a) + "456"
    
    return ANSWER@0.1
    '''

@lmql.query(merge=ByIntValue(score='mean'))
def final_answer(question):
    '''lmql
    if ctr2.value < 2:
        print("fail")
        ctr2()
        assert False, "failed"

    return ao_answer(question)
    '''

@lmql.query(merge=ByIntValue(score='mean'))
def final_answer2(question):
    '''lmql
    return final_answer(question)
    '''

if __name__ == "__main__":
    # graph query
    with lmql.traced("infer") as t:
        lmql.infer(final_answer2, question="What is 23*2-123?", 
                   state="graph.json", samples=5, parallel=1)
        print(lmql.certificate(t).asdict().get("metrics"))
    # to inspect the resulting graph, run 
    # lmql graph-watch graph.json 
    # and open http://localhost:1234 in your browser