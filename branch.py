import lmql
import inspect
from lmql.graphs.runtime import checkpoint
from lmql.runtime.loop import run_in_loop

# lmql.set_default_model(lmql.model("random", seed=123))

class Graph:
    def __init__(self):
        self.collected_resumables = []
        self.n = 0

    def branch(self, *values):
        def handler(resumable):
            choice = values[0]
            self.collected_resumables.extend([(v, resumable) for v in values if v is not choice])
            return values[0]
        return checkpoint(handler)

graph = Graph()

def branch(s):
    graph.n += 1
    print("branch called", graph.n)

    if graph.n == 1:
        return graph.branch(
            "Only Bob"
        )
    
    return graph.branch(
        "Bob",
        "Alice",
        "Charlie"
    )

@lmql.query
def q():
    '''lmql
    a = branch("")
    b = branch(a)
    print([a,b])
    "A:[A]" where len(TOKENS(A)) < 10
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