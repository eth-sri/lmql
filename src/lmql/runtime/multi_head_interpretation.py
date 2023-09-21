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
        # stateless configuration
        self.fct = fct
        self.context = context
        
        # additional function arguments
        self.args = args
        if self.args is None: self.args = ()
        self.kwargs = kwargs
        if self.kwargs is None: self.kwargs = {}

        # actual state
        self.current_args = None
        self.result = None

        self._iterator_fct = None
        self.trace = []
        self.future_trace = trace.copy() if trace is not None else []
        self.continue_last = continue_last

        self.fresh_copy = False

    def copy(self):        
        # self.result can be kept
        
        # continue with new head instance
        advanced_head = InterpretationHead(self.fct, None, self.args, self.kwargs, None, None)
        advanced_head.current_args = self.current_args
        advanced_head.result = self.result
        advanced_head._iterator_fct = self._iterator_fct
        advanced_head.trace = self.trace
        advanced_head.future_trace = self.future_trace
        advanced_head.continue_last = self.continue_last
        advanced_head.fresh_copy = True

        # reset current instance with corresponding future trace to allow fast-forwarding on re-entry
        self._iterator_fct = None
        # reset context
        self.context = None
        # move trace + future_trace to self.trace to enable re-entry1
        self.future_trace = deepcopy(self.trace) + deepcopy(self.future_trace)
        # clear trace, as iterator_fct will re-enter
        self.trace = []
        # if current_args is not None, we are in the middle of fulfilling a yield call (needs to be fast-forwarded and re-entrance)
        self.continue_last = self.current_args is not None

        self.current_args = None

        return advanced_head

    async def fast_forward(self):
        """
        Advances a new interpretation head according to self.trace, 
        by fulfilling all yield calls using the values in trace.
        """
        while len(self.future_trace) > 0:
            await self.continue_()

    async def advance(self, result):
        # make sure any interaction sets the fresh_copy flag to False
        self.fresh_copy = False
        
        await self.materialize_copy_if_necessary()
        
        self.trace.append(result)
        self.current_args = await self.iterator_fct().asend(result)
        await self.handle_current_arg()

    async def materialize_copy_if_necessary(self):
        # materialize lazy copy if not yet done
        if self._iterator_fct is None:
            if "__self__" in self.kwargs:
                self.kwargs["self"] = self.kwargs.pop("__self__")
            self._iterator_fct = self.fct(*self.args, **self.kwargs)

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
        # make sure any interaction sets the fresh_copy flag to False
        self.fresh_copy = False

        await self.materialize_copy_if_necessary()

        while self.current_args is None and self.result is None:
            self.current_args = await self.iterator_fct().__anext__()
            await self.handle_current_arg()

    def iterator_fct(self):
        # make sure any interaction with self._iterator_fct sets the fresh_copy flag to False
        self.fresh_copy = False
        return self._iterator_fct
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        return f"<InterpretationHead {self.fct.__name__}, {self.args}, {self.kwargs}, result={self.result}>"