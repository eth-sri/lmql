from typing import Optional, Any
from .node import *

class SubqueryOp(Node):
    def __init__(self, predecessors):
        super().__init__(predecessors)
        
        fct, args = predecessors
        assert hasattr(fct, "__lmql_query_function__"), f"InlineQueryCallOp only support LMQLQueryFunction as first argument, got {fct}"
        assert type(args) is Var, f"LMQL constraint function {fct} expects a single variable as argument, got {args}"

        self.runtime: Optional[Any] = None
        self.context: Optional[Any] = None
        self.variable = args

    def execute_predecessors(self, trace, context):
        return super().execute_predecessors(trace, context) + [context]

    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        
        fct = args[0]
        variable_value = args[1]
        
        # keep track of runtime (PromptInterpreter)
        self.context = args[2]
        self.runtime = args[2].runtime

        # print("variable_value", [variable_value])

        return True
    
    def follow(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        
        query_fct = args[0]
        variable_value = args[1]

        if variable_value is not None and self.context.final(self.variable.name) != "fin":
            subinterpreter = self.runtime.subinterpreter(id(self), query_fct.fct)
            return fmap(
                ("*", subinterpreter)
            )
            print("currently decoding", self.variable.name, variable_value)

        # if self.variable is not actively being decoded, this operation has no follow semantics
        return None
    
    def postprocess_var(self, var_name):
        return var_name == self.variable.name

    def postprocess(self, operands, value):
        query_fct = operands[0]
        subinterpreter = self.runtime.subinterpreter(id(self), query_fct.fct)
        # returning the subinterpreter as result means we return whatever the query program returns
        return subinterpreter
    
    def postprocess_order(self, other, operands, other_inputs, **kwargs):
        return 0 # other constraints cannot be compared
