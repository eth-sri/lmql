import lmql
import inspect
from lmql.graphs.runtime import branching_point
from lmql.runtime.loop import run_in_loop

# lmql.set_default_model(lmql.model("random", seed=123))

class Graph:
    def __init__(self):
        self.collected_resumables = []

    def branching_point(self, *values):
        def handler(resumable):
            choice = values[0]
            self.collected_resumables.extend([(v, resumable) for v in values if v is not choice])
            return values[0]
        return branching_point(handler)

graph = Graph()

def branch():
    return graph.branching_point(
        "Bob",
        "Alice"
    )

@lmql.query
def non_branch(name: str):
    '''lmql
    return name
    '''

@lmql.query
def q():
    '''lmql
    argmax(dump_compiled_code=True)
    "Is '{branch()}' and '{non_branch('Alice')}' the same name? (yes or no)\n"
    print([context.prompt])
    "A:[A]"
    print("answer is", [A])
    return context.prompt
    '''

res = [q()]
# print("p1", [p1])

with lmql.traced("resumed") as t:
    for value, resumable in graph.collected_resumables:
        res += [run_in_loop(resumable.copy()(value))]
        # print("extra", [res])
        # print(value, resumable)

    for r in res:
        print(r)