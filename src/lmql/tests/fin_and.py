import lmql
from lmql.tests.expr_test_utils import *
from lmql.ops.ops import digest, NextToken

# enable_show_transformed()

def compile_condition(c):
    q = lmql.query(f"argmax(__get_where__=True) 'Hello[TEST]' from 'openai/text-ada-001' where {c}")
    condition = lmql.main(q)[0]
    return condition

class FakeContext:
    def __init__(self, variables, variable_diffs, monotonicity):
        self.variables = variables
        self.variable_diffs = variable_diffs
        self.monotonicity = monotonicity
    
    def get(self, name, default=None):
        return self.variables[name]

    def get_diff(self, name, default=None):
        return self.variable_diffs[name]
    
    def final(self, name):
        return self.monotonicity[name]

@lmql_test
def test_var():
    expr = compile_condition('STOPS_AT(TEST, "\\n") and len(TEST) > 20')

    stops_at = expr.predecessors[0]
    len_op = expr.predecessors[1]
    
    # ctx = FakeContext({"TEST": "Hello World!\n"}, {"TEST": "\n"}, {"TEST": "inc"})
    ctx = FakeContext({"TEST": "Hello World!\n" + str(NextToken)}, {"TEST": "\n"}, {"TEST": "inc"})
    valid, final, trace, follow_trace = digest(expr, ctx, ctx)

    print("stops_at", follow_trace[stops_at])
    print("len_op", follow_trace[len_op])
    print("follow", follow_trace[expr])

test_var()