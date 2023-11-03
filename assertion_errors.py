import lmql
from lmql.graphs.merging import *
from random import random, seed

seed(123)

@lmql.query
def dep():
    '''lmql
    return 123
    '''

@lmql.query(decoder='sample')
def ao_answer(question):
    '''lmql
    a = dep()

    if random() < 0.5:
        assert False, "failed"
    print("result is", a)
    
    return "-78"@0.1
    '''

@lmql.query#(merge=ByIntValue(score='mean'))
def final_answer(question):
    '''lmql
    res = ao_answer(question)
    print("res is", [res])
    return res
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
        lmql.infer(final_answer, question="What is 23*2-123?", 
                   state="graph.json", samples=num_samples(), parallel=1)
        print(lmql.certificate(t).asdict().get("metrics"))
    # to inspect the resulting graph, run 
    # lmql graph-watch graph.json 
    # and open http://localhost:1234 in your browser