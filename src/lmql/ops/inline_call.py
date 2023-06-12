from typing import Optional, Any
from .node import *
from .booleans import *
import inspect

class InlineCallOp(Node):
    def __init__(self, predecessors, lcls, glbs):
        super().__init__(predecessors)
        
        fct, args = predecessors
        fct = fct.__lmql_query_function__

        variable_arg, self.args = args[0], args[1:]
        assert hasattr(fct, "__lmql_query_function__"), f"InlineQueryCallOp only support LMQLQueryFunction as first argument, got {fct}"
        assert type(variable_arg) is Var, f"LMQL constraint function {fct} expects a single variable as argument, got {args}"

        self.query_fct = fct
        self.variable = variable_arg

        self.captures = {}

        for i,arg in enumerate(fct.args):
            if arg in lcls.keys():
                self.captures[arg] = lcls[arg]
            elif arg in glbs.keys():
                self.captures[arg] = glbs[arg]
        
        # set positional arguments
        assert fct.function_context is not None, "LMQL in-context function " + str(fct) + " has no function context."
        signature: inspect.Signature = fct.function_context.argnames
        signature_args = signature.parameters
        
        # assert len(self.args) == len(signature_args), f"LMQL in-context function '{fct.name or str(fct)[:120]}' expects {len(signature_args)} positional arguments {fct.function_context.argnames} arguments, but got {len(self.args)} positional arguments: {self.args}"

        self.query_kwargs, _ = fct.make_kwargs(*self.args)

    def execute_predecessors(self, trace, context):
        return super().execute_predecessors(trace, context) + [context]

    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        
        # keep track of runtime (PromptInterpreter)
        context = args[-1]
        runtime = context.runtime

        si = self.subinterpreter(runtime, context.prompt)
        if not si in context.subinterpreter_results.keys():
            # print(f"internal warning: InlineCallOp could not find subinterpreter forward() result in context ProgramState: " + str(context.subinterpreter_results))
            return None
        return context.subinterpreter_results[si]
    
    def subinterpreter(self, runtime, prompt):
        return runtime.subinterpreter(id(self), prompt, self.query_fct, self.query_kwargs)

    def follow(self, *args, context=None, **kwargs):
        if any([a is None for a in args]): return None
        
        runtime = context.runtime

        si = self.subinterpreter(runtime, context.prompt)
        if not si in context.subinterpreter_results.keys():
            # print(f"internal warning: InlineCallOp could not find subinterpreter follow() result in context ProgramState: " + str(context.subinterpreter_results))
            return None
        
        return context.subinterpreter_results[si]
    
    def postprocess_var(self, var_name):
        return var_name == self.variable.name

    def postprocess(self, operands, value):
        fct, args, context = operands
        runtime = context.runtime
        # instructs postprocessing logic to use subinterpreters results as postprocessing results
        si = self.subinterpreter(runtime, context.prompt)
        return si
    
    def postprocess_order(self, other, operands, other_inputs, **kwargs):
        return 0 # other constraints cannot be compared

    @staticmethod
    def collect(op: Node):
        if isinstance(op, InlineCallOp):
            return [op]
        elif isinstance(op, AndOp) or isinstance(op, OrOp) or isinstance(op, NotOp):
            return [o for p in op.predecessors for o in InlineCallOp.collect(p)]
        else:
            # other operations do not have inline calls
            return []
        
    def __repr__(self):
        return str(self)

    def __str__(self) -> str:
        return f"<InlineCallOp {self.query_fct.name}({self.variable})>"