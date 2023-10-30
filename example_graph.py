import lmql

@lmql.query(merge=123)
def cot(question):
    '''lmql
    sample(verbose=True)
    
    "Q: {question} A: Let's think step by step (one sentences). [REASONING]" where len(TOKENS(REASONING)) < 20
    return REASONING
    '''

@lmql.query
def cot_answer(question) -> int: 
    '''lmql
    "Q: {question}\n A: {cot(question)} Thus the answer is[ANSWER]"
    return ANSWER
    '''

@lmql.query
def ao_answer(question) -> int:
    '''lmql
    "Q: {question}\n A: The answer is[ANSWER]"
    return ANSWER
    '''

@lmql.query
def answer(question):
    '''lmql
    return ao_answer(question) | cot_answer(question)
    '''

if __name__ == "__main__":
    # graph query
    lmql.infer(answer, question="What is 23*2?", state="graph.json", iterations=4)
    # to inspect the resulting graph, run 
    # lmql graph-watch graph.json 
    # and open http://localhost:1234 in your browser