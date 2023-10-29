import lmql

@lmql.query(merge=123)
def cot(question):
    '''lmql
    "Q: {question} A: Let's think step by step. [REASONING]"
    '''

@lmql.query
def cot_answer(question) -> int: 
    '''lmql
    "Q: {question}\n {cot(question)} A: [ANSWER: int]"
    return ANSWER
    '''

@lmql.query(confidence="abc")
def ao_answer(question) -> int:
    '''lmql
    "Q: {question}\n A: The answer (single number) is[ANSWER:int]"
    return ANSWER
    '''

@lmql.query
def answer(question):
    '''lmql
    ao_answer() | cot_answer(question)
    '''

if __name__ == "__main__":
    # graph query
    lmql.infer(answer, question="What is the answer to life, the universe and everything?", engine="threshold", budget=2)