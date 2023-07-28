import ast
import importlib
import os
import re
import sys
from _ast import (And, AsyncFunctionDef, Await, BinOp, Call, ClassDef, Compare, ExceptHandler,
                  FunctionDef, If, Import, ImportFrom, Return)
from io import StringIO
from typing import Any

import astunparse

import lmql.runtime.lmql_runtime as lmql_runtime
from lmql.language.fragment_parser import (FragmentParserError,
                                           LanguageFragmentParser,
                                           LMQLDecoderConfiguration, LMQLQuery)
from lmql.language.qstrings import (DistributionVariable, FExpression,
                                    TagExpression, TemplateVariable,
                                    qstring_to_stmts, stmts_to_qstring)
from lmql.language.validator import LMQLValidationError, LMQLValidator
from lmql.ops.ops import lmql_operation_registry
from lmql.runtime.dclib import get_all_decoders
from lmql.runtime.model_registry import model_name_aliases

OPS_NAMESPACE = "lmql.ops"
LIB_NAMESPACE = "lmql.lib"

class FreeVarCollector(ast.NodeVisitor):
    def __init__(self, free_vars, exclude_criteria=None):
        self.free_vars = free_vars
        
        self.exclude = exclude_criteria or []

    def is_excluded(self, name):
        for criterion in self.exclude:
            if type(criterion) is list:
                return name in criterion
            elif callable(criterion):
                return criterion(name)
            else:
                assert False, f"compiler error: invalid type for exclusion criterion in identifier collection: {type(criterion)}"
        return False

    def visit_Name(self, node):
        if type(node.ctx) is ast.Load:
            if self.is_excluded(node.id):
                return
            self.free_vars.add(node.id)

class DefinedVarsCollector(ast.NodeVisitor):
    def __init__(self, defined_vars, defined_constraints):
        self.defined_vars = defined_vars
        self.defined_constraints = defined_constraints

    def visit_Name(self, node):
        if type(node.ctx) is ast.Store:
            self.defined_vars.add(node.id)
        super().generic_visit(node)

    def visit_FunctionDef(self, node: FunctionDef) -> Any:
        self.defined_vars.add(node.name)
        super().generic_visit(node)

    def visit_ClassDef(self, node: ClassDef) -> Any:
        self.defined_vars.add(node.name)
        visit_potential_constraint_def(node, self)
        super().generic_visit(node)

    def visit_Import(self, node: Import) -> Any:
        for alias in node.names:
            self.defined_vars.add(alias.asname or alias.name)
        super().generic_visit(node)

    def visit_ImportFrom(self, node: ImportFrom) -> Any:
        for alias in node.names:
            self.defined_vars.add(alias.asname or alias.name)
        super().generic_visit(node)

    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> Any:
        self.defined_vars.add(node.name)
        super().generic_visit(node)

    # visit LMQLOp decorator to collect defined variables
    def visit_Call(self, node: ast.Call) -> Any:
        return super().generic_visit(node)

class PromptScope(ast.NodeVisitor):
    def __init__(self):
        self.distribution_vars = set()
        self.defined_vars = set()
        self.prologue_vars = set()
        self.free_vars = set()
        self.written_vars = set()

        self.defined_constraints = set()

    def scope_prologue(self, query: LMQLQuery):
        if query.prologue is None: return
        
        DefinedVarsCollector(self.prologue_vars, self.defined_constraints).visit(ast.parse(query.prologue))

    def scope(self, query: LMQLQuery):
        self.distribution_vars = set([query.distribution.variable_name]) if query.distribution is not None else set()    
        self.defined_vars = set()
        self.template_vars = set()
        self.prologue_vars = set()

        # collect set of global query template variables
        self.free_vars = set()
        self.written_vars = set()

        # collect defined vars in prologue
        self.scope_prologue(query)

        # collect defined vars in prompt
        for p in query.prompt: 
            self.visit(p)

        # also collect variable reads from where clause
        if query.where is not None:
            self.visit_where(query.where)
        if query.from_ast is not None:
            FreeVarCollector(self.free_vars, exclude_criteria=[self.exclude_identifier]).visit(query.from_ast)
        if query.decode is not None:
            FreeVarCollector(self.free_vars, exclude_criteria=[self.exclude_identifier]).visit(query.decode)
        if query.distribution is not None:
            FreeVarCollector(self.free_vars, exclude_criteria=[self.exclude_identifier]).visit(query.distribution.values)

        # remove all defined and prologue vars from free vars
        self.free_vars = self.free_vars - self.defined_vars - self.prologue_vars - self.defined_constraints

        query.scope = self

    def visit_where(self, node):
        FreeVarCollector(self.free_vars, exclude_criteria=[self.exclude_identifier]).visit(node)

    def visit_Expr(self, expr):
        if type(expr.value) is ast.Constant:
            self.scope_Constant(expr.value)
        else:
            super().generic_visit(expr)

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if is_query_string_with_constraints(node):
            self.scope_Constant(node.values[0])
            for constraint in node.values[1:]:
                self.visit_where(constraint)
        else:
            super().generic_visit(node)

    def scope_Constant(self, node):
        if type(node.value) is not str: return super().visit_Constant(node)
        qstring = node.value

        stmts = qstring_to_stmts(qstring, mode="all")

        # capture set of defined vars
        declared_template_vars = [v.name for v in stmts if type(v) is TemplateVariable]
        for v in declared_template_vars: 
            self.defined_vars.add(v)
            self.written_vars.add(v)
            self.template_vars.add(v)
            if v in self.free_vars: self.free_vars.remove(v)

        used_fstring_expr = [s.expr for s in stmts if type(s) is FExpression]
        for v in used_fstring_expr:
            try:
                parsed = ast.parse(v, mode="eval")
                self.visit(parsed)
            except Exception as e:
                print("info: failed to parse fstring expression: ", [v])
                raise e
                # raise RuntimeError("Failed to parse fstring expression: ", v)
                return super().visit_Constant(node)

        def transform_qexpr(qexpr):
            if type(qexpr) is TemplateVariable and qexpr.name in self.distribution_vars:
                return DistributionVariable(qexpr.name)
            if type(qexpr) is FExpression:
                return FExpression(f"lmql.lmql_runtime.f_escape({qexpr.expr})")
            elif type(qexpr) is TagExpression:
                return TagExpression(f"lmql.lmql_runtime.tag(\"{qexpr.tag[1:]}\")")
            return str(qexpr)

        node.value = stmts_to_qstring([transform_qexpr(s) for s in stmts])

        return super().visit_Constant(node)

    def exclude_identifier(self, name):
        # make sure "input" can be intercepted
        if name in ["input"]:
            return False
        if name in ["lmql", "context", "__dynamic__"]:
            return True
        if name in self.free_vars:
            return True
        if name in self.written_vars:
            return True
        # exclude LMQL built-ins
        if get_builtin_name(name) is not None:
            return True
        # exclude Python built-ins
        if __builtins__.get(name) is not None:
            return True
        if name in get_all_decoders():
            return True
        return False

    def visit_Name(self, node: ast.Name):
        name = str(node.id)
        
        if type(node.ctx) is ast.Store:
            self.written_vars.add(name)
            if name in self.free_vars:
                self.free_vars.remove(name)
            
        if type(node.ctx) is ast.Load:
            if self.exclude_identifier(name):
                return
            self.free_vars.add(name)
        
        return True
    
    def visit_ExceptHandler(self, node: ExceptHandler) -> Any:
        self.written_vars.add(node.name)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: FunctionDef) -> Any:
        self.defined_vars.add(node.name)
    
    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> Any:
        self.defined_vars.add(node.name)

    def visit_ClassDef(self, node: ClassDef) -> Any:
        self.defined_vars.add(node.name)
        visit_potential_constraint_def(node, self)

    def visit_ImportFrom(self, node: ImportFrom) -> Any:
        for alias in node.names:
            self.defined_vars.add(alias.asname or alias.name)

def visit_potential_constraint_def(node: ClassDef, scope: PromptScope):
    for d in node.decorator_list:
        # detect LMQLOp calls
        if type(d) is ast.Call:
            if type(d.func) is ast.Name:
                if d.func.id == "LMQLOp" and len(d.args) == 1:
                    if type(d.args[0]) is ast.Constant:
                        scope.defined_constraints.add(d.args[0].value)
                    elif type(d.args[0]) is ast.List:
                        for e in d.args[0].elts:
                            if type(e) is ast.Constant:
                                scope.defined_constraints.add(e.value)

def is_query_string_with_constraints(node: ast.BoolOp):
    if len(node.values) < 1:
        return False
    left_most_operand = node.values[0]
    return type(left_most_operand) is ast.Constant and type(left_most_operand.value) is str and isinstance(node.op, ast.And)

class FunctionCallTransformation(ast.NodeTransformer):
    """
    Translates function calls into lmql.call calls (to enable automatic await and unpacking 
    when calling subqueries).
    """
    def visit_Await(self, node: Await) -> Any:
        super().generic_visit(node)

        if type(node.value) is ast.Await:
            return node.value
        return node.value

    def is_excluded_from_call_transformation(self, node):
        if not type(node) is ast.Name: return False
        if ast.unparse(node).startswith("lmql.runtime_support.call"): return True
        return node.id in ["print", "eval", "locals", "globals"]

    def visit_Call(self, node: Call) -> Any:
        f = self.visit(node.func)
        args = [self.visit(a) for a in node.args]
        keywords = [self.visit(k) for k in node.keywords]

        if self.is_excluded_from_call_transformation(node.func):
            node.func = f
            node.args = args
            node.keywords = keywords
            return node

        wrapped = Call(ast.parse("lmql.runtime_support.call"), [f, *args], keywords)
        wrapped = ast.Await(wrapped)

        return wrapped
class PromptClauseTransformation(FunctionCallTransformation):
    """
    Transformes string expressions on statement level to model queries.
    """
    
    def __init__(self, query):
        self.query = query
    
    def transform(self):
        self.query.prompt = [self.visit(p) for p in self.query.prompt]

    def visit_Expr(self, expr):
        if type(expr.value) is ast.Constant:
            expr.value = self.transform_Constant(expr.value)
            return expr
        else:
            return self.generic_visit(expr)

    # translate id access to context
    def visit_Name(self, node: ast.Name):
        name = str(node.id)
        
        if type(node.ctx) is ast.Load:
            if name == "context":
                return ast.parse("(" + yield_call("get_context", ()) + ")").body[0].value
        return node

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if is_query_string_with_constraints(node):
            left_most_operand = node.values[0]
            if len(node.values[1:]) > 1:
                constraints_expression = ast.BoolOp(op=node.op, values=node.values[1:])
            if len(node.values[1:]) == 1:
                constraints_expression = node.values[1]
            elif len(node.values[1:]) == 0:
                constraints_expression = None
            return self.transform_Constant(left_most_operand, constraints = constraints_expression)
        return self.generic_visit(node)

    def transform_Constant(self, constant, constraints=None):
        if type(constant.value) is not str: return constant
        
        qstring = constant.value
        if len(qstring) == 0: return constant
        if qstring.strip().startswith("lmql"): return constant

        qstring = qstring.encode("unicode_escape").decode("utf-8").encode('unicode_escape').decode('utf-8')        
        compiled_qstring = ""

        declared_template_vars = set()

        for stmt in qstring_to_stmts(qstring, mode="square-only"):
            if type(stmt) is str:
                compiled_qstring += stmt
            elif type(stmt) is DistributionVariable:
                compiled_qstring += str(stmt)
            elif type(stmt) is TemplateVariable:
                declared_template_vars.add(stmt.name)
                compiled_qstring += str(stmt)

        # keep track of last stmt in this qstring
        last_stmt = stmt

        if len(compiled_qstring) == 0:
            return constant
        
        qstring_as_fstring: ast.JoinedStr = ast.parse(f'f"""{compiled_qstring}"""').body[0].value
        function_call_transformer = FunctionCallTransformation()
        qstring_as_fstring.values = [function_call_transformer.visit(v) for v in qstring_as_fstring.values]

        if constraints is not None:
            constraint_transformation = InlineConstraintsTransformation(constraints, scope=self.query.scope)
            code_str, result_reference = constraint_transformation.transform()
            result_code = code_str + "\n"

            # result_code = f'yield context.query(f"""{compiled_qstring}""")'
            result_code += interrupt_call('query', f'f"""{compiled_qstring}"""', "{**globals(), **locals()}", "constraints=" + result_reference)
        else:
            result_code = interrupt_call('query', f'f"""{compiled_qstring}"""', "{**globals(), **locals()}")

        for v in declared_template_vars:
            get_var_call = yield_call('get_var', f'"{v}"')
            result_code += f"\n{v} = " + get_var_call

        return ast.parse(result_code)

    # def transform_prompt_stmt(self, stmt):
    #     if type(stmt) is ast.Expr:
    #         if type(stmt.value) is ast.Constant and type(stmt.value.value) is str:
    #             # print(stmt.value.value)
    #             stmt.value = self.transform_query_string(stmt.value.value)
    #             # print(dir(stmt.value))
    #     else:
    #         print(type(stmt))
    #     return stmt

class SNFList:
    def __init__(self):
        self.stmts = []
        self.var_counter = 0

    def add(self, expr):
        vname = f"intm{self.var_counter}"
        self.var_counter += 1
        self.stmts.append(f"{vname} = {expr.strip()}")
        return vname

    def ast(self):
        return ast.parse("\n".join(self.stmts))
    
    def last_var(self):
        assert self.var_counter > 0, "No last variable available (0 statements in SNF)."
        return f"intm{self.var_counter - 1}"

    def str(self):
        return "\n".join(self.stmts)

class NameVisitor(ast.NodeVisitor):
    def __init__(self, name_visitor):
        self.name_visitor = name_visitor

    def visit_Name(self, node):
        self.name_visitor(node)


class NameTransformer(ast.NodeTransformer):
    def __init__(self, name_transformer):
        self.name_transformer = name_transformer

    def visit_Name(self, node):
        return self.name_transformer(node)

class ReturnStatementTransformer(ast.NodeTransformer):
    def __init__(self, query):
        self.query = query
    
    def transform(self):
        self.query.prompt = [self.visit(p) for p in self.query.prompt]

    def visit_FunctionDef(self, node: FunctionDef) -> Any:
        # do not recurse into nested functions
        return node
    
    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> Any:
        # do not recurse into nested functions
        return node

    def visit_Return(self, node):
        return ast.parse("yield ('result', " + astunparse.unparse(node.value).strip() + ")")

class LMQLConstraintTransformation:
    def __init__(self, scope) -> None:
        self.scope = scope

    def transform_name(self, node, keep_variables=False, plain_python=False):
        # check for built-ins
        bn = get_builtin_name(node, plain_python)
        if bn is not None: return bn
        # check if variable is distribution variable
        if node.id in self.scope.distribution_vars:
            raise LMQLValidationError("Distribution variable {} cannot be used in where clause.".format(node.id))

        # check for template variables
        if node.id in self.scope.template_vars and not keep_variables:
            return f"lmql.runtime_support.Var('{node.id}')"
        else:
            return f"lmql.runtime_support.Var('{node.id}', python_variable=True, python_value={node.id})"

        return bn or node.id

    def transform_node(self, expr, snf):
        if type(expr) is ast.BoolOp:
            if type(expr.op) is ast.And or type(expr.op) is ast.Or:
                ops = expr.values
                tops = [self.transform_node(op, snf) for op in ops]
                tops_list = ",\n  ".join([t.strip() or "None" for t in tops])
                
                Op = f"{OPS_NAMESPACE}.AndOp" if type(expr.op) is ast.And else f"{OPS_NAMESPACE}.OrOp"
                return snf.add(f"{Op}([\n  {tops_list}\n])")
        elif type(expr) is ast.Name:
            return self.transform_name(expr)
        elif type(expr) is ast.UnaryOp:
            op = expr.op
            
            Ops = {
                ast.Not: f"{OPS_NAMESPACE}.NotOp"
            }

            for OpT, impl in Ops.items():
                if type(op) is OpT:
                    operand = self.transform_node(expr.operand, snf).strip()
                    return snf.add(f"{impl}([{operand}])")

            assert False, "unary operator {} not supported.".format(type(expr.op))
        elif type(expr) is ast.Compare:
            op = expr.ops[0]
            assert len(expr.ops) == 1, "compiler currently does not support comparison with more than one operator"
            
            Ops = {
                ast.Eq: f"{OPS_NAMESPACE}.EqOp",
                ast.Lt: f"{OPS_NAMESPACE}.Lt",
                ast.Gt: f"{OPS_NAMESPACE}.Gt",
                ast.In: f"{OPS_NAMESPACE}.InOp"
            }

            for OpT, impl in Ops.items():
                if type(op) is OpT: 
                    ops = [self.transform_node(c, snf) for c in [expr.left] + expr.comparators]
                    ops_list = ", ".join(ops).strip()
                    return snf.add(f"{impl}([{ops_list}])")
            
            if is_type_constraint(expr):
                type_name = expr.comparators[0].id
                var_name = expr.left.args[0].id
                return snf.add(f"{OPS_NAMESPACE}.CallOp([{LIB_NAMESPACE}.types.is_type, [{OPS_NAMESPACE}.Var('{var_name}'), {type_name}]], locals(), globals())")
                # return snf.add(f"{LIB_NAMESPACE}.is_type([{type_name}, {OPS_NAMESPACE}.Var('{var_name}')])")
            
            assert False, "operator {} is not supported.".format(astunparse.unparse(expr))
        elif type(expr) is ast.Constant:
            return self.default_transform_node(expr, snf).strip()
        elif type(expr) is ast.ListComp:
            return self.default_transform_node(expr, snf).strip()
        elif type(expr) is ast.Call:
            constraint_ref = get_builtin_name(expr.func) or get_inner_constraint_ref(expr.func, self.scope)
            if constraint_ref is not None:
                args = [self.transform_node(a, snf) for a in expr.args]
                args_list = ", ".join(args)
                return f"{constraint_ref}([{args_list}])"
            if is_allowed_builtin_python_call(expr.func):
                return self.default_transform_node(expr, snf).strip()
            
            assert type(expr.func) is ast.Name, "In LMQL constraint expressions, only function calls to direct function references are allowed: {}".format(astunparse.unparse(expr))
            tfunc = ast.unparse(expr.func)
            targs = [self.transform_node(a, snf) for a in expr.args]
            kwargs = [f"('__kw:{e.arg}', {self.transform_node(e.value, snf)})" for e in expr.keywords]
            targs_list = ", ".join(targs + kwargs)

            return f"{OPS_NAMESPACE}.CallOp([{tfunc}, [{targs_list}]], locals(), globals())"
        elif type(expr) is ast.List:
            return self.default_transform_node(expr, snf).strip()

        print(f"compiler warning: expressions of type {type(expr)} are not explicitly supported: '{astunparse.unparse(expr).strip()}'")
        return snf.add(self.default_transform_node(expr, snf))

    def default_transform_node(self, node, snf):
        # collect the set of captured template variables
        names = set()
        def collect_name(node):
            name = node.id
            if name in self.scope.template_vars:
                names.add(name)
        NameVisitor(collect_name).visit(node)
        names = sorted(list(names))

        # if no template variable names are capture, node represents a constant expression
        if len(names) == 0: return astunparse.unparse(node)

        def transform_name(node):
            node.id = self.transform_name(node, keep_variables=True, plain_python=True)
            return node
        node = NameTransformer(transform_name).visit(node)

        args = (" " + ", ".join(names)) if len(names) > 0 else ""
        var_ops = (", ".join([f"{OPS_NAMESPACE}.Var('{n}')" for n in names])).strip() if len(names) > 0 else ""
        fct_code = astunparse.unparse(node).strip()
        
        return f"{OPS_NAMESPACE}.OpaqueLambdaOp([lambda{args}: {fct_code}, {var_ops}])"

class WhereClauseTransformation(LMQLConstraintTransformation):
    def __init__(self, query: LMQLQuery):
        super().__init__(scope=query.scope)
        self.query = query
        
        assert self.scope is not None, "WhereClauseTransformation requires a scoped query for transformation"
    
    def transform(self):
        snf = SNFList()
        
        if self.query.where is None:  return None
        if type(self.query.where) is ast.Expr: 
            self.query.where = self.query.where.value

        result = self.transform_node(self.query.where, snf=snf)

        self.query.where = snf.str()
        self.query.where_expr = result

class InlineConstraintsTransformation(LMQLConstraintTransformation):
    def __init__(self, expression: ast.BoolOp, scope):
        super().__init__(scope=scope)
        self.expression = expression
    
    def transform(self):
        snf = SNFList()
        
        if self.expression is None:  return None
        if type(self.expression) is ast.Expr: 
            self.expression = self.expression.value

        result = self.transform_node(self.expression, snf=snf)

        return snf.str(), result


def is_allowed_builtin_python_call(node):
    if type(node) is not ast.Name:
        return False
    allowed_builtin_functions = set(["set", "all"])
    return node.id in allowed_builtin_functions

def get_inner_constraint_ref(node, scope: PromptScope):
    if type(node) is str:
        n = node
    else:
        if type(node) is not ast.Name:
            return None
        n = node.id
    
    if n in scope.defined_constraints:
        return OPS_NAMESPACE + ".lmql_operation_registry['" + n + "']"
    
    return None

def get_builtin_name(node, plain_python=False):
    if type(node) is str:
        n = node
    else:
        if type(node) is not ast.Name:
            return None
        n = node.id
    
    if n in lmql_operation_registry.keys():
        name = lmql_operation_registry[n]
        if type(name) is type:
            return OPS_NAMESPACE + ".lmql_operation_registry['" + n + "']"
        else:
            return OPS_NAMESPACE + "." + name

    return None

def is_type_constraint(expr: ast.Expr):
    if not type(expr.left) is ast.Call:
        return False
    if not type(expr.left.func) is ast.Name:
        return False
    if not expr.left.func.id == "type":
        return False
    if not type(expr.ops[0]) is ast.Is:
        return False
    if not len(expr.comparators) == 1:
        return False
    right = expr.comparators[0]
    if not type(right) is ast.Name:
        return False
    if not len(expr.left.args) == 1:
        return False
    if not type(expr.left.args[0]) is ast.Name:
        return False
    
    return True

class DecodeClauseTransformation:
    def __init__(self, query):
        self.query = query

    def transform(self):
        if type(self.query.decode) is ast.Name:
            method = ast.Constant(self.query.decode.id, "str")
            keyword_args = []
            self.query.decode = LMQLDecoderConfiguration(method, keyword_args)
        elif type(self.query.decode) is ast.Call:
            method = ast.Constant(self.query.decode.func.id, "str")
            keyword_args = self.query.decode.keywords
            self.query.decode = LMQLDecoderConfiguration(method, keyword_args)
        else:
            assert False, "cannot handle decode clause {} ()".format(self.query.decode, type(self.query.decode))


        return self.query

class CompilerTransformations:
    def __init__(self):
        self.transformations = [
            PromptClauseTransformation,
            WhereClauseTransformation,
            DecodeClauseTransformation,
            ReturnStatementTransformer
        ]
    
    def transform(self, query):
        for T in self.transformations:
            t = T(query).transform()
        return query

class PythonFunctionWriter:
    def __init__(self, name, filename, parameters, prologue, decorators=None, decorators_args=None):
        self.name = name
        self.filename = filename
        self.parameters = parameters
        self.prologue = prologue
        
        self.in_memory_contents = ""
        
        self.file = open(self.filename, "w")

        self.indent = "  "
        self.write("import lmql\nimport lmql.lib\n")
        self.write(self.prologue)
        
        if decorators is not None:
            if decorators_args is None:
                decorators_args = [None] * len(decorators)
            for d,args in zip(decorators, decorators_args):
                self.write(f"@{d}({args})\n")
        self.write(f"async def {self.name}({self.make_kwargs()}):\n")

    def write(self, code):
        self.in_memory_contents += code
        self.file.write(code)

    def make_kwargs(self):
        if len(self.parameters) == 0:
            return ""
        return ",".join(f"{p}=None" for p in self.parameters)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.file.close()

    def add(self, code):
        if code is None:
            return
        for line in code.split("\n"):
            if line.strip() == "": continue
            self.write(f"{self.indent} {line}\n")

class LMQLModule(object):
    def __init__(self, compiled_file, lmql_code=None, output_variables=None):
        self.compiled_file = compiled_file
        self._code = None
        self.lmql_code = lmql_code
        self.output_variables = output_variables or []

    def load(self):
        sys.path.append(os.path.dirname(self.compiled_file))
        m = __import__(os.path.basename(self.compiled_file[:-3]))
        for v in m.__dict__.values():
            if type(v) is lmql_runtime.LMQLQueryFunction:
                v.lmql_code = self.lmql_code
        setattr(m, "code", self.code)
        setattr(m, "lmql_code", self.lmql_code)
        return m

    def __str__(self):
        with open(self.compiled_file, "r") as f:
            return f.read()

    def code(self):
        if self._code is None:
            with open(self.compiled_file, "r") as f:
                self._code = f.read()
        return self._code

def unparse_list(ast_elements):
    return ", ".join([astunparse.unparse(e).strip() for e in ast_elements])

def preprocess_text(lmql_code):
    if lmql_code.startswith("lmql"):
        lmql_code = lmql_code[4:]
    while lmql_code.startswith("\n") or lmql_code.startswith(" "):
        if lmql_code.startswith("\n"):
            lmql_code = lmql_code[1:]
            break
        else:
            lmql_code = lmql_code[1:]
    
    # remove common indent
    lines = lmql_code.split("\n")
    common_indent = min([len(l) - len(l.lstrip()) for l in lines if len(l.strip()) > 0])
    return "\n".join([l[common_indent:] for l in lines])

def yield_call(func, *args):
    return f"""yield lmql.runtime_support.context_call("{func}", {", ".join([str(a) for a in args])})"""

def interrupt_call(func, *args):
    return f"""yield lmql.runtime_support.interrupt_call("{func}", {", ".join([str(a) for a in args])})"""

class LMQLCompiler:
    def __init__(self):
        pass

    def compile(self, filepath):
        try:
            # parse file
            with open(filepath) as f:
                contents = f.read()
            lmql_code = preprocess_text(contents)
            buf = StringIO(lmql_code)
            parser = LanguageFragmentParser()
            try:
                q = parser.parse(buf.readline)
            except IndentationError as e:
                raise RuntimeError("parsing error: {}.\nFailed when parsing:\n {}".format(e, lmql_code))

            # output file path
            basename = os.path.basename(filepath).split(".lmql")[0]
            output_file = os.path.join(os.path.dirname(filepath), f"{basename}_compiled.py")

            # scoping
            scope = PromptScope()
            scope.scope(q)

            # validation
            LMQLValidator().validate(q)

            # compilation
            transformations = CompilerTransformations()
            transformations.transform(q)

            model_name = astunparse.unparse(q.from_ast).strip()
            model_name = model_name_aliases.get(model_name, model_name)
            if model_name[1:-1] in model_name_aliases.keys():
                model_name = "'" + model_name_aliases[model_name[1:-1]] + "'"

            # resulting code
            code = None
            output_variables = "output_variables=[" + ", ".join([f'"{v}"' for v in scope.defined_vars]) + "]"

            # generate function that runs query
            parameters = list(sorted(list(scope.free_vars)))

            with PythonFunctionWriter("query", output_file, parameters, 
                q.prologue, decorators=["lmql.compiled_query"], decorators_args=[output_variables]) as writer:
                
                writer.add(yield_call("set_decoder", astunparse.unparse(q.decode.method).strip(), unparse_list(q.decode.decoding_args)))                
                writer.add(yield_call("set_model", model_name))
                writer.add("# where")
                writer.add(q.where)
                writer.add(yield_call("set_where_clause", q.where_expr))
                writer.add("# prompt")
                writer.add(astunparse.unparse(q.prompt))
                if q.distribution:
                    writer.add("# distribution")
                    # writer.add("context.set_distribution('{}', {})".format(q.distribution.variable_name, astunparse.unparse(q.distribution.values).strip()))
                    writer.add(yield_call("set_distribution", "\"" + q.distribution.variable_name + "\"", astunparse.unparse(q.distribution.values).strip()))
                
                writer.add(f"yield ('result', (" + yield_call("get_return_value", ()) + "))")

            if q.decode.has_dump_compiled_code_flag:
                print(writer.in_memory_contents)

            return LMQLModule(output_file, lmql_code=lmql_code, output_variables=[v for v in scope.defined_vars])
        except FragmentParserError as e:
            sys.stderr.write("error: " + str(e) + "\n")
            sys.exit(1)

