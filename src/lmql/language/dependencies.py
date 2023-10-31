"""
Compile static analysis path that tracks sub-query dependencies.
"""
from _ast import Assign
import ast
from ast import *
from typing import Any

def remove(scope, names):
    if type(scope) is str:
        return scope if scope not in names else None
    return [remove(s, names) for s in scope if remove(s, names) is not None]

def map_scope(scope, fct):
    if type(scope) is str:
        return fct(scope)
    return [map_scope(s, fct) for s in scope]

class QueryDependencyScope(ast.NodeVisitor):
    def __init__(self):
        # list of dependencies, elements of type list, express
        # a disjunction over sub-dependencies
        self._dependencies = []
        self.assigned_variables = []

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
        
        # detect branching a() | b() calls 
        # track dependencies of
        if ast.unparse(func) == "lmql.runtime_support.branch":
            subscopes = []
            assert len(node.args) == 1, "QueryDependencyScope: expected branch call with exactly one argument, but found {}".format(len(node.args))
            branched_calls = node.args[0]
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

        # otherwise track as normal dependency
        self.visit(func)
        
        args = node.args
        for a in args:
            self.visit(a)
        
        if len(args) == 0:
            return node

        if ast.unparse(func) != "lmql.runtime_support.call" and ast.unparse(func) != "lmql.runtime_support.defer_call":
            return node
        
        target = args[0]
        if type(target) is not ast.Name:
            return node
        
        self._dependencies.append(ast.unparse(target))

        return node
    