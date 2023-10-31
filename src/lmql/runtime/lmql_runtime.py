"""
Runtime support used by compiled LMQL query code.
"""

import inspect
from dataclasses import dataclass
from typing import Any, Dict, Optional
from lmql.graphs import branch, defer_call, call, annotate_score, scorer

from lmql.ops.ops import *
from lmql.runtime.context import Context
from lmql.runtime.output_writer import silent
from lmql.runtime.postprocessing.group_by import GroupByPostprocessor
from lmql.api.inspect import is_query
from lmql.runtime.formatting import format, tag
from lmql.runtime.query_function import LMQLQueryFunction, FunctionContext, LMQLInputVariableScope, EmptyVariableScope

def context_call(fct_name, *args, **kwargs):
    return ("call:" + fct_name, args, kwargs)

def interrupt_call(fct_name, *args, **kwargs):
    return ("interrupt:" + fct_name, args, kwargs)

def compiled_query(output_variables=None, dependencies=None, group_by=None):
    if output_variables is None:
        output_variables = []
    
    postprocessors = []
    
    calling_frame = inspect.stack()[1]
    
    if group_by is not None:
        postprocessors.append(GroupByPostprocessor(group_by))
    
    # TODO validate that only one postprocessor is used

    def func_transformer(fct):
        return LMQLQueryFunction(fct, 
                                 output_variables=output_variables, 
                                 postprocessors=postprocessors, 
                                 scope=LMQLInputVariableScope(fct, calling_frame),
                                 dependencies=dependencies)
    return func_transformer
    

def type_expr(var_name, target, lcls, glbs, *args, **kwargs):
    """
    Transforms expressions in query strings like "Hello [WHO: <expr>]" into
    their constraint equivalent.
    """
    if is_query(target):
        return InlineCallOp([target, list((Var(var_name),) + args)], lcls, glbs)
    elif type(target) is str:
        return RegexOp([Var(var_name), target])
    elif target is int:
        return IntOp([Var(var_name)])
    else:
        raise TypeError("Not a valid type expression or tactic annotation '" + str(target) + "' for variable '" + var_name + "'.")