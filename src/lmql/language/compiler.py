import ast
import sys
import astunparse
import os
import importlib
import re

from io import StringIO
from lmql.ops.ops import lmql_operation_registry

from lmql.language.qstrings import qstring_to_stmts, TemplateVariable
from lmql.language.validator import LMQLValidator, LMQLValidationError
from lmql.language.fragment_parser import LMQLDecoderConfiguration, LMQLQuery, LanguageFragmentParser, FragmentParserError

class PromptScope(ast.NodeVisitor):
    def scope(self, query: LMQLQuery):
        self.distribution_vars = set([query.distribution.variable_name]) if query.distribution is not None else set()    
        self.defined_vars = set()

        # collect set of global query template variables
        self.template_variables = list()

        for p in query.prompt: self.visit(p)

        query.scope = self

    def visit_Constant(self, node):
        if type(node.value) is not str: return super().visit_Constant(node)
        qstring = node.value

        # capture set of defined vars
        declared_template_vars = [v.name for v in qstring_to_stmts(qstring) if type(v) is TemplateVariable]
        for v in declared_template_vars: self.defined_vars.add(v)

        used_template_vars = [v[1:-1] for v in re.findall("\{[A-z0-9]+\}", qstring)]
        for v in used_template_vars:
            if v not in self.defined_vars and v not in self.template_variables: 
                self.template_variables.append(v)

        return super().visit_Constant(node)

    def visit_Name(self, node):
        return True

class QueryStringTransformation(ast.NodeTransformer):
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
        else:
            self.generic_visit(expr)
        return expr

    def transform_Constant(self, constant):
        if type(constant.value) is not str: return constant
        qstring = constant.value
        # TODO: handle escaping more completely and gracefully
        qstring = qstring.replace("\n", "\\\\n")
        compiled_qstring = ""

        declared_template_vars = set()

        for i, stmt in enumerate(qstring_to_stmts(qstring)):
            if type(stmt) is str:
                compiled_qstring += stmt
            elif type(stmt) is TemplateVariable:
                if stmt.name in self.query.scope.distribution_vars:
                    compiled_qstring += f"[distribution:{stmt.name}]"
                else:
                    declared_template_vars.add(stmt.name)
                    compiled_qstring += "[" + stmt.name + "]"

        result_code = f'yield context.query(f"""{compiled_qstring}""")'

        for v in declared_template_vars:
            result_code += f"\n{v} = context.get_var('{v}')"
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

    def visit_Return(self, node):
        return ast.parse("yield ('result', " + astunparse.unparse(node.value).strip() + ")")

class WhereClauseTransformation():
    def __init__(self, query: LMQLQuery):
        self.query = query
        self.scope: PromptScope = query.scope

        assert self.scope is not None, "WhereClauseTransformation requires a scoped query for transformation"
    
    def transform(self):
        snf = SNFList()
        
        if self.query.where is None:  return None
        if type(self.query.where) is ast.Expr: 
            self.query.where = self.query.where.value

        result = self.transform_node(self.query.where, snf=snf)

        self.query.where = snf.str()
        self.query.where_expr = result

    def transform_name(self, node, keep_variables=False, plain_python=False):
        # check for built-ins
        bn = get_builtin_name(node, plain_python)
        if bn is not None: return bn
        # check if variable is distribution variable
        if node.id in self.scope.distribution_vars:
            raise LMQLValidationError("Distribution variable {} cannot be used in where clause.".format(node.id))

        # check for template variables
        if node.id in self.scope.defined_vars and not keep_variables:
            return f"lmql.Var('{node.id}')"

        return bn or node.id

    def transform_node(self, expr, snf):
        if type(expr) is ast.BoolOp:
            if type(expr.op) is ast.And or type(expr.op) is ast.Or:
                ops = expr.values
                tops = [self.transform_node(op, snf) for op in ops]
                tops_list = ",\n  ".join([t.strip() or "None" for t in tops])
                
                Op = "lmql.AndOp" if type(expr.op) is ast.And else "lmql.OrOp"
                return snf.add(f"{Op}([\n  {tops_list}\n])")
        # elif type(expr) is ast.Call:
        #     tfunc = self.transform_node(expr.func, snf)
        #     targs = [self.transform_node(a, snf) for a in expr.args]
        #     targs_list = ", ".join(targs)
        #     return f"{tfunc}({targs_list})"
        elif type(expr) is ast.Name:
            return self.transform_name(expr)
        elif type(expr) is ast.UnaryOp:
            op = expr.op
            
            Ops = {
                ast.Not: "lmql.NotOp"
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
                ast.Eq: "lmql.EqOp",
                ast.Lt: "lmql.Lt",
                ast.Gt: "lmql.Gt",
                ast.In: "lmql.InOp"
            }

            for OpT, impl in Ops.items():
                if type(op) is OpT: 
                    ops = [self.transform_node(c, snf) for c in [expr.left] + expr.comparators]
                    ops_list = ", ".join(ops).strip()
                    return snf.add(f"{impl}([{ops_list}])")
            
            assert False, "operator {} is not supported.".format(astunparse.unparse(expr))
        elif type(expr) is ast.Constant:
            return self.default_transform_node(expr, snf).strip()
        elif type(expr) is ast.ListComp:
            return self.default_transform_node(expr, snf).strip()
        elif type(expr) is ast.Call:
            bn = get_builtin_name(expr.func)
            if bn is not None:
                args = [self.transform_node(a, snf) for a in expr.args]
                args_list = ", ".join(args)
                return f"{bn}([{args_list}])"
            if is_allowed_builtin_python_call(expr.func):
                return self.default_transform_node(expr, snf).strip()
        elif type(expr) is ast.List:
            return self.default_transform_node(expr, snf).strip()

        print(f"compiler warning: expressions of type {type(expr)} are not explicitly supported: '{astunparse.unparse(expr).strip()}'")
        return snf.add(self.default_transform_node(expr, snf))

    def default_transform_node(self, node, snf):
        # collect the set of captured template variables
        names = set()
        def collect_name(node):
            name = node.id
            if name in self.scope.defined_vars:
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
        var_ops = (", ".join([f"lmql.Var('{n}')" for n in names])).strip() if len(names) > 0 else ""
        fct_code = astunparse.unparse(node).strip()
        
        return f"lmql.OpaqueLambdaOp([lambda{args}: {fct_code}, {var_ops}])"

def is_allowed_builtin_python_call(node):
    if type(node) is not ast.Name:
        return False
    allowed_builtin_functions = set(["set", "all"])
    return node.id in allowed_builtin_functions

def get_builtin_name(node, plain_python=False):
    if type(node) is not ast.Name:
        return None
    n = node.id
    
    mapped_builtins = {
        "SELECT": "lmql.SelectOp",
        "len": "lmql.LenOp",
        "raw_constant": "lmql.RawValueOp"
    }
    builtins = set(["ENTITIES"])

    if n in builtins or n.upper() in builtins: 
        return "lmql." + n.lower()
    elif n in mapped_builtins.keys() and not plain_python:
        return mapped_builtins[n]
    elif n in lmql_operation_registry.keys() and not plain_python:
        return lmql_operation_registry[n]
    else:
        return None

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
            QueryStringTransformation,
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
        self.write("import lmql.runtime.lmql_runtime as lmql\n")
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
    def __init__(self, compiled_file, lmql_code=None):
        self.compiled_file = compiled_file
        self._code = None
        self.lmql_code = lmql_code

    def load(self):
        sys.path.append(os.path.dirname(self.compiled_file))
        m = __import__(os.path.basename(self.compiled_file[:-3]))
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

class LMQLCompiler:
    def __init__(self):
        pass

    def compile(self, filepath):
        try:
            # parse file
            with open(filepath) as f:
                contents = f.read()
            lmql_code = contents
            buf = StringIO(contents)
            parser = LanguageFragmentParser()
            q = parser.parse(buf.readline)

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

            # resulting code
            code = None

            # generate function that runs query
            with PythonFunctionWriter("query", output_file, list(scope.template_variables) + ["context"], 
                q.prologue, decorators=["lmql.query"]) as writer:
                
                writer.add(f"context.set_model({astunparse.unparse(q.from_ast).strip()})")
                writer.add(f"context.set_decoder({astunparse.unparse(q.decode.method).strip()}, {unparse_list(q.decode.decoding_args)})")
                writer.add("# where")
                writer.add(q.where)
                writer.add(f"context.set_where_clause({q.where_expr})")
                writer.add("# prompt")
                writer.add(astunparse.unparse(q.prompt))
                if q.distribution:
                    writer.add("# distribution")
                    writer.add("context.set_distribution('{}', {})".format(q.distribution.variable_name, astunparse.unparse(q.distribution.values).strip()))
                
                writer.add(f"yield ('result', context.get_return_value())")

                code = writer.in_memory_contents

            return LMQLModule(output_file, lmql_code=lmql_code)
        except FragmentParserError as e:
            sys.stderr.write("error: " + str(e) + "\n")

