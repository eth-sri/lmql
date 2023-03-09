import asyncio
from lmql.runtime.multi_head_interpretation import InterpreterReturnValue, InterpreterCall, InterpretationHead, ContinueOnly

async def fun2(context):
    result = []
    a = yield context.query("a")
    result.append(a)
    b = yield context.query("b")
    result.append(b)
    c = yield context.query("c")
    result.append(c)

    yield InterpreterReturnValue(result)

class Context:
    def query(self, value):
        return InterpreterCall(value)

async def assert_remaining_trace(head, expected, message):
    if head.waiting:
        value = await head.continue_()
    else:
        if head.iterator_fct is None:
            await head.materialize_copy_if_necessary()
        value = head.last_call_args
        if value is None: value = [None]

    if head.done:
        trace = []
    else:
        trace = [value[0]]

        while not head.done:
            await head.advance(value)
            value = await head.continue_()
            if not head.done:
                trace.append(value[0])

    assert str(trace) == str(expected), f"{message}. Expected {expected}, got {trace}"

async def test_multi_head():
    ctx = Context()
    
    # simple head
    start_head = InterpretationHead(fun2, ctx)
    await assert_remaining_trace(start_head, ["a", "b", "c"], "simple head")

    # continued head
    continued_head = InterpretationHead(fun2, ctx)
    await continued_head.continue_()
    await assert_remaining_trace(continued_head, ["a", "b", "c"], "continued head")

    # copy start_head
    start_head = InterpretationHead(fun2, ctx)
    copy_start_head = start_head.copy()
    await assert_remaining_trace(copy_start_head, ["a", "b", "c"], "copied start_head")

    # copy continued_head
    continued_head = InterpretationHead(fun2, ctx)
    await continued_head.continue_()
    copy_continued_head = continued_head.copy()
    await assert_remaining_trace(copy_continued_head, ["a", "b", "c"], "copied continued_head")

    # double copy simple head
    start_head = InterpretationHead(fun2, ctx)
    copy_start_head = start_head.copy()
    copy_copy_start_head = copy_start_head.copy()
    await assert_remaining_trace(copy_copy_start_head, ["a", "b", "c"], "double copied start_head")

    # double copy continued head
    continued_head = InterpretationHead(fun2, ctx)
    await continued_head.continue_()
    copy_continued_head = continued_head.copy()
    copy_copy_continued_head = copy_continued_head.copy()
    await assert_remaining_trace(copy_copy_continued_head, ["a", "b", "c"], "double copied continued_head")

    # advanced head
    start_head = InterpretationHead(fun2, ctx)
    value = await start_head.continue_()
    await start_head.advance(value)
    assert(start_head._internal_trace == [("a",)])
    await assert_remaining_trace(start_head, ["b", "c"], "advanced head")

    # copy advanced head
    start_head = InterpretationHead(fun2, ctx)
    value = await start_head.continue_()
    await start_head.advance(value)
    copy_start_head = start_head.copy()
    assert(copy_start_head.trace == [("a",)])
    assert(copy_start_head._internal_trace == [])
    await assert_remaining_trace(copy_start_head, ["b", "c"], "copied advanced head")

    # copy advanced, continued head
    start_head = InterpretationHead(fun2, ctx)
    value = await start_head.continue_()
    await start_head.advance(value)
    await start_head.continue_()
    copy_start_head = start_head.copy()
    
    assert(copy_start_head.trace == [("a",), ContinueOnly])
    assert(copy_start_head._internal_trace == [])
    await assert_remaining_trace(copy_start_head, ["b", "c"], "copied advanced head")

    # double copy advanced, continued head
    start_head = InterpretationHead(fun2, ctx)
    value = await start_head.continue_()
    await start_head.advance(value)
    await start_head.continue_()
    copy_copy_start_head = start_head.copy().copy()
    
    assert(copy_copy_start_head.trace == [("a",), ContinueOnly])
    assert(copy_copy_start_head._internal_trace == [])
    await assert_remaining_trace(copy_copy_start_head, ["b", "c"], "copied advanced head")

    # copy advanced, continued head but advance prototype first
    start_head = InterpretationHead(fun2, ctx)
    value = await start_head.continue_()
    await start_head.advance(value)
    value = await start_head.continue_()

    copy_start_head = start_head.copy()
    await start_head.advance(value)

    assert(copy_start_head.trace == [("a",), ContinueOnly])
    assert(copy_start_head._internal_trace == [])
    await assert_remaining_trace(copy_start_head, ["b", "c"], "copied advanced head")
    
    assert start_head._internal_trace == [("a",), ("b",)]

if __name__ == "__main__":
    asyncio.run(test_multi_head())