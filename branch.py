import lmql
import inspect
import asyncio
from lmql.graphs.runtime import checkpoint
from lmql.runtime.loop import run_in_loop
from lmql.runtime.lmql_runtime import call

lmql.set_default_model(lmql.model("random", seed=123))
global i
i = 0

global resumables
resumables = []

def branch(s):
    async def handler(resumable):
        global i
        global resumables
        i += 1
        resumables += [resumable]

        assert i > 1, "fail for first call"
            
        return s + str(i)
    return checkpoint(handler)

class NamedRuntime:
    def __init__(self, name) -> None:
        self.name = name
    """
    Default LMQL runtime to use for sub-query resolution.
    """
    async def call(self, fct, *args, **kwargs):
        print('call dispatched via', self.name)
        return await call(fct, *args, **kwargs)

def another():
    return 123

@lmql.query
async def q():
    '''lmql
    s = branch("hi")
    a = another()
    return "return with" + s + str(a)
    '''

async def main():
    r1 = NamedRuntime("r1")

    try:
        print(await q(runtime=r1))
    except AssertionError:
        print("call 1 failed")
        pass

    r2 = NamedRuntime("r2")
    print("===== RESUME 1")
    for r in resumables:
        print(await r("resumed-1", runtime=r2))
    
    r3 = NamedRuntime("r3")
    print("===== RESUME 2")
    for r in resumables:
        print(await r("resumed-2", runtime=r3))

if __name__ == "__main__":
    asyncio.run(main())