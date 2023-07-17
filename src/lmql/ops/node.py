from tokenize import Token
from typing import Iterable, Tuple, List
from itertools import product

from lmql.ops.token_set import *
from lmql.ops.follow_map import *

class Node:
    def __init__(self, predecessors):
        assert type(predecessors) is list, "Predecessors must be a list, not {}".format(type(predecessors))
        self.predecessors = predecessors
        self.depends_on_context = False
    
    def execute_predecessors(self, trace, context):
        return [execute_op(p, trace=trace, context=context) for p in self.predecessors]

    def forward(self, *args, **kwargs):
        raise NotImplementedError(type(self) + " does not implement forward()")

    def follow(self, *args, **kwargs):
        raise NotImplementedError(type(self) + " does not implement follow()")
    
    def final(self, args, **kwargs):
        if all([a == "fin" for a in args]):
            return "fin"
        return "var"

    def __nodelabel__(self):
        return str(type(self))
    
    def postprocess_var(self, var_name):
        """
        Returns true if this operations provides postprocessing semantics for complete values for the given variable name.
        """
        return False

    def postprocess(self, operands, value):
        """
        Returns the postprocessed variant of `value`. Only called if `postprocess_var` returns true for variable name of value.
        
        You can return a tuple of postprocessed_rewrite (prompt) and postprocessed_value (variable value), to additionally 
        provide different postprocessing semantics for the variable value and the rewrite of the prompt.
        """
        pass

    def postprocess_order(self, other, **kwargs):
        """
        Orders application of postprocessing operations. Returns "before", "after" or 0 if order is not defined.
        
        Only invoked for `other` operations, that return true for the same `postprocess_var`.
        """
        return 0 # by default, no order is defined (only one postprocessing operation per variable can be applied)


class Var(Node):
    def __init__(self, name, python_variable=False, python_value=None):
        super().__init__([])
        self.name = name
        
        self.python_variable = python_variable
        self.python_value = python_value

        self.depends_on_context = True
        
        # indicates whether the downstream node requires text diff information
        self.diff_aware_read = False

    async def json(self):
        return self.name

    def forward(self, context, **kwargs):
        if self.python_variable:
            return context.python_scope.get(self.name)

        if self.diff_aware_read:
            return (context.get(self.name, None), context.get_diff(self.name, None))
        
        return context.get(self.name, None)
    
    def follow(self, context, **kwargs):
        if self.python_variable:
            return context.python_scope.get(self.name)

        value = context.get(self.name, None)
        if value is None: return None
        
        # also return the text diff if required
        if self.diff_aware_read:
            value = (value, context.get_diff(self.name, None))

        # strip_next_token but also supports tuples
        def strip_nt(v):
            if type(v) is tuple: return (strip_next_token(v[0]), v[1])
            else: return strip_next_token(v)

        return fmap(
            ("eos", PredeterminedFinal(strip_nt(value), "fin")),
            ("*", value),
        )

    def final(self, x, context, operands=None, result=None, **kwargs):
        if self.python_variable:
            return "fin"
        return context.final(self.name)

    def __repr__(self) -> str:
        return f"<Var {self.name}>"


def create_mask(follow_map, valid, final):
    if follow_map is None:
        return "*"
    
    allowed_tokens = tset()
    otherwise_result = None

    for pattern, result in follow_map:
        if pattern == "*":
            otherwise_result = result

        if result is not None:
            value, final = result
        else:
            value = None
            final = "var"

        if value == True or value is None:
            allowed_tokens = union(allowed_tokens,pattern)
        elif value == False and final == ("var",):
            allowed_tokens = union(allowed_tokens, pattern)
        elif value is None and len(follow_map.components) == 1:
            allowed_tokens = "*"
        elif result == (False, ('fin',)):
            if pattern != "*":
                allowed_tokens = setminus(allowed_tokens, pattern)

    if allowed_tokens == "∅":
        return tset("eos")

    if len(allowed_tokens) == 0:
        if otherwise_result is not None:
            othw_value, othw_final = otherwise_result
        else:
            othw_value, othw_final = None, "var"
        if not othw_value and othw_final == ("fin",):
            return tset("eos")
        else:
            return "*"

    return allowed_tokens

def is_node(op):
    return issubclass(type(op), Node)

def derive_predecessor_final(op, trace):
    def get_final(v):
        # for nodes, get final value from trace
        if is_node(v): return trace[v][1]
        # for constants, final value is always "fin"
        return "fin"
    return [get_final(p) for p in op.predecessors]

def derive_final(op, trace, context, result):
    predecessor_final = derive_predecessor_final(op, trace)

    def get_predecessor_result(v):
        if is_node(v): return trace[v][0]
        return v
    
    predecessor_values = [get_predecessor_result(p) for p in op.predecessors]

    context_arg = ()
    if op.depends_on_context: 
        context_arg += (context,)
    
    return op.final(predecessor_final, *context_arg, operands=predecessor_values, result=result)

def execute_op(op: Node, trace=None, context=None, return_final=False, semantics="forward"):
    # for constant dependencies, just return their value
    if not is_node(op): 
        return op
    
    # only evaluate each operation once
    if op in trace.keys(): 
        return trace[op][0]
    
    # compute predecessor values
    inputs = op.execute_predecessors(trace, context)
    
    if op.depends_on_context: 
        inputs += (context,)

    inputs_final = derive_predecessor_final(op, trace)
    semantics_fct = op.__getattribute__(semantics)
    result = semantics_fct(*inputs, final=inputs_final)
    is_final = derive_final(op, trace, context, result)
    
    if trace is not None: 
        trace[op] = (result, is_final)

    if return_final:
        return result, is_final

    return result

def digest(expr, context, follow_context, no_follow=False):
    if expr is None: return True, "fin", {}, {}

    trace = {}
    follow_trace = {}
    expr_value, is_final = execute_op(expr, trace=trace, context=context, return_final=True)

    if no_follow:
        return expr_value, is_final, trace, follow_trace

    for op, value in trace.items():
        # determine follow map of predecessors
        if len(op.predecessors) == 0: 
            # empty argtuple translates to no follow input
            intm = all_fmap((ArgTuple(), ["fin"])) 
        else:
            # use * -> value, for constant value predecessor nodes
            def follow_map(p):
                if is_node(p): return follow_trace[p]
                else: return fmap(("*", (p, ("fin",))))
            intm = fmap_product(*[follow_map(p) for p in op.predecessors])
        
        # apply follow map
        op_follow_map = follow_apply(intm, op, value, context=follow_context)

        # name = op.__class__.__name__
        # print(name, value)
        # print("follow({}) = {}".format(name, op_follow_map))

        follow_trace[op] = op_follow_map
    
    return expr_value, is_final, trace, follow_trace

NextToken = "<lmql.next>"

def is_next_token(t): 
    return t == NextToken

def strip_next_token(x):
    if type(x) is list:
        return [i for i in x if not is_next_token(i)]
    elif type(x) is tuple:
        return tuple(i for i in x if not is_next_token(i))
    if type(x) is not str:
        return x
    if x.endswith(NextToken):
        x = x[:-len(NextToken)]
    return x

class postprocessed_value:
    def __init__(self, value):
        self.value = value
class postprocessed_rewrite:
    def __init__(self, rewrite):
        self.rewrite = rewrite

