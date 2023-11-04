import lmql
from lmql.graphs.merging import *

from random import random, seed

lmql.set_default_model(lmql.model("random"))

seed(43)
ctr = {'value': 1}
m = lmql.model("random")

@lmql.query(model=m)
async def a_0():
    '''lmql
    try:
        assert ctr['value'] > 1
    finally:
        ctr['value'] += 1

    return "a" + str(ctr['value'])
    '''

@lmql.query(model=m)
async def b_0():
    '''lmql
    return "b" + str(ctr['value'])
    '''

@lmql.query(model=m)
async def a():
    '''lmql

    r = a_0() | b_0()

    return r + 'both'
    '''

@lmql.query(model=m)
async def one(i=0):
    '''lmql
    return "one of " + a()
    '''

if __name__ == "__main__":
    # graph query
    with lmql.traced("infer") as t:
        lmql.infer(one, state="graph.json", parallel=1)
        print(lmql.certificate(t).asdict().get("metrics"))
    # to inspect the resulting graph, run 
    # lmql graph-watch graph.json 
    # and open http://localhost:1234 in your browser