"""
Compile static analysis path that tracks sub-query dependencies.
"""
from _ast import Assign
import ast
from ast import *
from typing import Any
from .compiled_call import CompiledCall

def remove(scope, names):
    """
    Removes all scope entries that reference one of the given names 
    from the given query dependency set.
    """
    if type(scope) is tuple:
        query_call_repr = scope[0]
        query_name = query_call_repr.split("(",1)[0]
        return scope if query_name not in names else None
    return [remove(s, names) for s in scope if remove(s, names) is not None]

def map_scope(scope, fct):
    """
    Maps references to query functions in the given query dependency 
    set to the result of the given function.

    E.g. [('a', 'some_query')] -> [('a', fct('some_query'))]
    """
    if type(scope) is tuple:
        return (scope[0], fct(scope[1]))
    return [map_scope(s, fct) for s in scope]

class QueryDependencyScope(ast.NodeVisitor):
    def __init__(self):
        # list of dependencies, elements of type list, express
        # a disjunction over sub-dependencies
        self._dependencies = []
        self.assigned_variables = []

    def dependency_dict(self, dependencies=None):
        """
        Formats the queries dependencies as a dictionary, as included in emitted code.
        """
        dependencies = dependencies or self._dependencies
        counts = {}
        s = ""

        for entry in dependencies:
            if type(entry) is tuple:
                repr, target = entry
                if repr in counts:
                    counts[repr] += 1
                    repr += f"#{counts[repr]}"
                else:
                    counts[repr] = 1
                
                repr = repr.replace("'", "\\'")
                s += f"('{repr}', '{ast.unparse(target)}'),"
            elif type(entry) is list:
                s += self.dependency_dict(entry) + ","
        s.rstrip(",")
        return "[" + s + "]"

    def effective_dependencies(self):
        return remove(self._dependencies, self.assigned_variables)

    def scope(self, query):
        for p in query.prompt:
            self.visit(p)
        return self.effective_dependencies()

    def visit_Assign(self, node: Assign) -> Any:
        self.assigned_variables.append(ast.unparse(node.targets[0]))
        self.visit(node.value)
        return node

    def visit_Call(self, node: Call) -> Any:
        func = node.func
        call = CompiledCall.view(node)

        # detect branching a() | b() calls 
        if ast.unparse(call.func) == "lmql.runtime_support.branch":
            subscopes = []
            assert len(call.args) == 2, "QueryDependencyScope: expected branch call with exactly two arguments, but found {}".format(len(call.args))
            branched_calls = call.args[1]
            assert isinstance(branched_calls, ast.List), "QueryDependencyScope: expected branch call with a list of dependencies, but found {}".format(type(branched_calls))

            subscopes = []

            for v in branched_calls.elts:
                scope = QueryDependencyScope()
                scope.visit(v)
                subdependencies = scope.effective_dependencies()
                if len(subdependencies) == 1:
                    subscopes.append(subdependencies[0])
                else:
                    subscopes.append(subdependencies)

            self._dependencies.append(subscopes)
            return
        
        # visit recursively
        self.visit(func)
        
        args = node.args
        for a in args:
            self.visit(a)
        
        if len(args) == 0:
            return node
        
        # check for compiled function calls
        call = CompiledCall.view(node)
        if not type(call) is CompiledCall:
            return self.visit_defered_call(node)

        self._dependencies.append((self.dependency_repr(call.func, call.args, call.keywords), call.func))

        return node
    
    def dependency_repr(self, func, args, keywords):
        repr_s = ast.unparse(func) + "(" + ", ".join([ast.unparse(a) for a in args])
        if kwargs := keywords:
            for kw in kwargs:
                key = kw.arg
                if key == "__branch_score__":
                    continue
                repr_s += ", " + key + "=" + ast.unparse(kw.value)
        repr_s += ")"
        return repr_s

    def visit_defered_call(self, node: ast.Call) -> Any:
        func = node.func
        args = node.args
        
        # visit recursively
        self.visit(func)
        for a in args:
            self.visit(a)
        
        # check for deferred function calls
        if len(args) == 0:
            return node

        if ast.unparse(node.func) == "lmql.runtime_support.defer_call":
            target = node.args[0]
            args = node.args[1:]
            kwargs = node.keywords

            self._dependencies.append((self.dependency_repr(target, args, kwargs), target))
            
        return node