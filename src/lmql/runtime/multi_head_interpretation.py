import asyncio

class InterpreterReturnValue:
    def __init__(self, value):
        self.value = value

class InterpreterCall:
    def __init__(self, *args, loc=None):
        self.args = args
        self.loc = loc

class InterpreterHeadPool:
    def __init__(self, fct, context, trace=None):
        self.heads = [InterpretationHead(fct, context, trace=trace)]

        self.done = False
        self.result = [None]

    async def advance(self, handler):
        new_heads = []
        
        for h in self.heads:
            args = await h.continue_()
            if h.done: 
                new_heads += [h]
                continue
            result = await handler(*args)
            new_heads += await h.advance(result)
        
        self.heads = new_heads[:5]
        
        self.result = [h.result for h in self.heads]
        self.done = all(h.done for h in self.heads)


class ContinueOnly: pass

def deepcopy(v):
    if isinstance(v, list):
        return [deepcopy(i) for i in v]
    elif isinstance(v, dict):
        return {k: deepcopy(v) for k,v in v.items()}
    else:
        return v

class ReplayingContextWrapper(object):
    """
    Returns the cached result (replays) the first len(self.value_cache) calls to 
    the wrapped object's methods, if they occur in self.cached_attrs.
    """

    def __init__(self, wrappee, cached_attrs=None, cache=None):
        self.wrappee = wrappee

        self.cached_attrs = cached_attrs or set()
        self.cached_attrs.add("get_var")
        self.num_replays = 0
        
        self.value_cache = []
        if cache is not None:
            self.value_cache = cache
            self.replaying = True
        else:
            self.replaying = False
        self.replay_counts = {}

    def copy(self):
        return ReplayingContextWrapper(self.wrappee, self.cached_attrs, cache=deepcopy(self.value_cache))

    def __getattr__(self, attr):
        if attr in ["cached_attrs", "value_caches", "replaying", "wrappee", "copy"]:
            return super().__getattr__(attr)

        if not attr in self.cached_attrs:
            return getattr(self.wrappee, attr)
        
        def fct(*args, **kwargs):
            # replace all cached calls
            if self.replaying:
                if len(self.value_cache) <= self.num_replays:
                    self.replaying = False
                else:
                    value = self.value_cache[self.num_replays]
                    self.num_replays += 1
                    # print("replaying {} call to".format(self.num_replays), attr, "with", args, kwargs, " as", type(value), [value])
                    return value
            
            # otherwise keep recording
            result = getattr(self.wrappee, attr)(*args, **kwargs)
            self.value_cache += [result.copy() if hasattr(result, "copy") else result]
            # print("value_cache", self.value_cache)
            return result
        return fct

class InterpretationHeadDone(Exception):
    pass

class InterpretationHead:
    def __init__(self, fct, context, args=None, kwargs=None, trace=None):
        self.fct = fct
        self.context = context
        self.context_wrapped = ReplayingContextWrapper(context)
        self.user_state = None
        
        # additional function arguments
        self.args = args
        if self.args is None: self.args = ()
        self.kwargs = kwargs
        if self.kwargs is None: self.kwargs = {}
        
        # to be given at instantiation
        self.trace = [] if trace is None else trace
        # to be recorded by this head
        self._internal_trace = []

        self.iterator_fct = None
        self.queue = []

        self.done = False
        self.result = None

        self.last_call_args = None
        self.waiting = True

        self.id = "h"
        self.copies = 0

    def get_context(self):
        self.context_wrapped.wrappee = self.context
        return self.context_wrapped

    def copy(self, next_value=None, context=None):
        # construct trace for copy
        if len(self._internal_trace) > 0:
            trace = self._internal_trace.copy()
        else:
            trace = self.trace.copy()
        
        if next_value is not None: 
            trace.append(next_value)
        if not self.waiting and (len(trace) == 0 or trace[-1] is not ContinueOnly):
            trace.append(ContinueOnly)
        # construct new head
        if context is None: 
            context = self.context
        
        c = InterpretationHead(self.fct, self.context, args=self.args, kwargs=self.kwargs, trace=trace)
        c.context_wrapped = self.context_wrapped.copy()
        c.id = self.id + "_" + str(self.copies)
        c.user_state = self.user_state
        self.copies += 1

        c.waiting = self.waiting

        return c

    @property
    def num_calls(self):
        return len(self._internal_trace)

    @property
    def num_all_calls(self):
        return len(self.trace) + len(self._internal_trace)

    async def fast_forward(self):
        """
        Advances a new interpretation head according to self.trace, 
        by fulfilling all yield calls using the values in trace.
        """
        if self.iterator_fct is None:
            self.iterator_fct = self.fct(*self.args, **self.kwargs, context=self.get_context())

        while len(self.trace) > 0:
            await self.continue_()
            v = self.trace[0]
            self.trace = self.trace[1:]
            if v is ContinueOnly:
                assert len(self.trace) == 0, "ContinueOnly must be the last element in trace."
                break
            await self.advance(v)

    async def advance(self, result):
        await self.materialize_copy_if_necessary()
        
        # guard against advancing a finished head
        if self.done: raise InterpretationHeadDone()

        assert not self.done, "Cannot advance() a finished interpreter head (check self.done)."
        assert not self.waiting, "Cannot advance() a non-waiting interpreter head. Must call continue_ first."

        self.last_call_args = None
        self.waiting = True

        self._internal_trace += [result]
        try:
            self.queue.append((await self.iterator_fct.asend(result)))
        except StopAsyncIteration as e:
            raise InterpretationHeadDone(e)

        return [self]

    async def materialize_copy_if_necessary(self):
        # materialize lazy copy if not yet done
        if self.iterator_fct is None:
            self.iterator_fct = self.fct(*self.args, **self.kwargs, context=self.get_context())

            if len(self.trace) > 0:
                await self.fast_forward()

    async def continue_(self):
        await self.materialize_copy_if_necessary()
        
        if len(self.queue) == 0:
            self.queue.append(await self.iterator_fct.__anext__())

        value = self.queue[0]
        self.queue = self.queue[1:]

        if type(value) is InterpreterReturnValue:
            self.done = True
            self.result = value.value
            return None
        elif type(value) is tuple and len(value) == 2 and value[0] == "result":
            # consider ("result", <expr>) yields as return statements
            # this avoids a dependency on this file from LMQL compiled modules
            self.done = True
            self.result = value[1]
            return None
        else:
            self.last_call_args = value.args
            self.waiting = False
            
            return self.last_call_args

class BranchingPoint:
    def __init__(self, values):
        self.values = values

class MultiHeadInterpretedFunction:
    def __init__(self, fct):
        self.fct = fct
        self.ctr = 0

    async def __call__(self, *args, **kwargs):
        pool = InterpreterHeadPool(self.fct, self)
        while not pool.done:
            await pool.advance(self.do_query)
        for i,r in enumerate(pool.result):
            print(f"head {i} result: ", r)
        return pool.result

    async def do_query(self, prompt):
        return BranchingPoint([
            "0","1"
        ])

    def query(self, prompt, loc):
        return InterpreterCall(prompt, loc=loc)

def multi_head(fct):
    return MultiHeadInterpretedFunction(fct)

@multi_head
async def fun(context):
    all_values = []
    a = yield context.query("Query A", loc="a")
    all_values.append(a)
    
    for i in range(5):
        b = yield context.query("Query B", loc="b")
        all_values.append(b)
    
    yield InterpreterReturnValue(all_values)
