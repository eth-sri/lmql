from functools import reduce
import itertools
from parser.ast import Expression, FunctionCall, Identifier
from lib.state import ProgramState

flatten_unique = lambda xs: list(set(reduce(lambda a, b: a + b, xs)))

def jit(e: Expression, state: ProgramState):
    code, names = compile_and_track(e)
    expr_lambda = eval("lambda " + ",".join(names) + ": " + code, state.globals)
    return lambda state: expr_lambda(*[state.resolve(n) for n in names])

def compile_and_track(e: Expression):
    if type(e) is Identifier:
        return e.name, [e.name]
    elif type(e) is FunctionCall:
        arg_results = [compile_and_track(a) for a in e.args]
        args = ",".join([a[0] for a in arg_results])
        names = flatten_unique([a[1] for a in arg_results])
        return f"{e.function_name}({args})", names