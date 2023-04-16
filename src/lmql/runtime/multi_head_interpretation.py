import asyncio

class InterpreterCall:
    def __init__(self, *args, loc=None):
        self.args = args
        self.loc = loc

class ContinueOnly: pass

def deepcopy(v):
    if isinstance(v, list):
        return [deepcopy(i) for i in v]
    elif isinstance(v, dict):
        return {k: deepcopy(v) for k,v in v.items()}
    else:
        return v

class InterpretationHeadDone(Exception): 
    def __init__(self, result):
        self.result = result

class InterpretationHead:
    def __init__(self, fct, context, args=None, kwargs=None, trace=None, continue_last=False):
        self.fct = fct
        self.context = context
        
        # additional function arguments
        self.args = args
        if self.args is None: self.args = ()
        self.kwargs = kwargs
        if self.kwargs is None: self.kwargs = {}

        self.current_args = None
        self.result = None

        self.iterator_fct = None
        self.trace = []
        self.future_trace = trace.copy() if trace is not None else []
        self.continue_last = continue_last

    def copy(self):
        return InterpretationHead(self.fct, None, self.args, self.kwargs, deepcopy(self.trace) + deepcopy(self.future_trace), self.current_args is not None)

    async def fast_forward(self):
        """
        Advances a new interpretation head according to self.trace, 
        by fulfilling all yield calls using the values in trace.
        """
        while len(self.future_trace) > 0:
            await self.continue_()

    async def advance(self, result):
        await self.materialize_copy_if_necessary()
        
        self.trace.append(result)
        self.current_args = await self.iterator_fct.asend(result)
        await self.handle_current_arg()

    async def materialize_copy_if_necessary(self):
        # materialize lazy copy if not yet done
        if self.iterator_fct is None:
            self.iterator_fct = self.fct(*self.args, **self.kwargs)

            if len(self.future_trace) > 0:
                await self.fast_forward()

    async def handle_current_arg(self):
        if type(self.current_args) is tuple and len(self.current_args) >= 2 and self.current_args[0].startswith("call:"):
            function_name = self.current_args[0][5:]
            assert hasattr(self.context, function_name), f"call: expected function {function_name} to be defined in context"
            fct = getattr(self.context, function_name)
            if len(self.future_trace) > 0:
                res = self.future_trace.pop(0)
                await self.advance(res)
                return
            else:
                res = await fct(*self.current_args[1], **self.current_args[2])
                await self.advance(res)
                return
        elif type(self.current_args) is tuple and len(self.current_args) >= 2 and self.current_args[0].startswith("interrupt:"):
            function_name = self.current_args[0][10:]
            fct = getattr(self.context, function_name)
            res = await self.context.query(*self.current_args[1], **self.current_args[2])
            assert type(res) is InterpreterCall, f"interrupt: expected InterpreterCall, got {type(res)}"
            self.current_args = res.args
            if len(self.future_trace) > 0:
                res = self.future_trace.pop(0)
                await self.advance(res)
            return
        elif type(self.current_args) is tuple and len(self.current_args) == 2 and self.current_args[0] == "result":
            # consider ("result", <expr>) yields as return statements
            # this avoids a dependency on this file from LMQL compiled modules
            self.result = self.current_args[1]
            raise InterpretationHeadDone(self.result)
        else:
            assert False, f"unexpected yield self.current_args from compiled function: {self.current_args}"

    async def continue_(self):
        await self.materialize_copy_if_necessary()

        while self.current_args is None and self.result is None:
            self.current_args = await self.iterator_fct.__anext__()
            await self.handle_current_arg()