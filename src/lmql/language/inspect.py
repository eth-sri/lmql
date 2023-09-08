"""
Similar to 'inspect' module, but for LMQL queries.
"""

import inspect
from lmql.runtime.lmql_runtime import is_query

def getsource(fct):
    """
    Returns the source code of the given LMQL query function.
    """
    assert is_query(fct), f"getsource() expects a LMQL query function, got {fct}"
    return fct.lmql_code

def getcompiled(fct):
    """
    Returns the compiled code of the given LMQL query function.
    """
    assert is_query(fct), f"getcompiled() expects a LMQL query function, got {fct}"
    return inspect.getsource(fct.__lmql_query_function__.fct)