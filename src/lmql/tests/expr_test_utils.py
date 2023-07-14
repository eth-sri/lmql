import sys
import ast
import asyncio
import types
import astunparse
import inspect
import termcolor
from lmql.language.fragment_parser import LMQLQuery
from lmql.language.compiler import PromptScope, SNFList, WhereClauseTransformation
from lmql.ops.ops import NextToken, digest
from lmql.runtime.program_state import ProgramState
from lmql.runtime.lmql_runtime import LMQLQueryFunction


global show_transformed
show_transformed = False

SEQ = "<SEQ placeholder>"

class LMQLExpr: 
    def __init__(self, node):
        self.node = node
    
    def follow(self, seq, variable_name="SEQ"):
        for (result, final), follow_map in self.digest(seq, variable_name=variable_name, return_follow_map=True):
            yield follow_map

    def digest(self, seq, variable_name="SEQ", return_follow_map=False, debug=False):
        sequence = seq
        if type(sequence) is str:
            sequence = sequence.split(" ")
        full_text = ""

        program_variables = ProgramState("")
        
        digested = []
        results = []

        for tok in sequence:
            added = (" " if len(full_text) > 0 else "") + tok
            full_text += added
            text = full_text

            # current context
            program_variables = program_variables.copy()
            program_variables.set(variable_name, text, "inc")

            # follow context
            follow_program_variables = program_variables.copy()
            follow_program_variables.set(variable_name, text + NextToken, "inc")

            # digest token with where expr
            result, is_final, trace, follow_trace = digest(self.node,
                context=program_variables,
                follow_context=follow_program_variables
            )

            if type(result) is list: 
                result = tuple(result)
            
            if return_follow_map:
                yield (result, is_final), self.node.follow_map
            else:
                if debug:
                    print(full_text, result, is_final)
                yield (result, is_final)

class LMQLExpressionCompiler(ast.NodeTransformer):
    def __init__(self, expr_compiler):
        self.expr_compiler: WhereClauseTransformation = expr_compiler
        self.expr_compiler.scope.defined_vars.add("SEQ")

    def visit_Assert(self, node):
        if node.msg is None:
            node.msg = ast.Constant(f"Line {node.lineno}: Assertion '{astunparse.unparse(node).strip()}' failed.", kind="str")
        return node
    
    def visit_Call(self, node):
        translated_calls = set(["inc", "dec", "fin", "var"])
        if type(node.func) is ast.Name and node.func.id in translated_calls:
            return ast.Call(
                ast.Name("raw_constant"),
                node.args + [ast.Constant(node.func.id, "str")],
                []
            )
        node.args = [self.visit(a) for a in node.args]

        return node

    def visit_Assign(self, node: ast.Assign):
        if type(node.value) is ast.Call:
            if type(node.value.func) is ast.Name and node.value.func.id == "LMQLExpr":
                call = self.visit(node.value)
                snf = SNFList()
                
                direct_result = self.expr_compiler.transform_node(call.args[0], snf)
                value = ast.Name(snf.last_var()) if snf.var_counter > 0 else ast.parse(direct_result.strip())

                return ast.copy_location(ast.Expr([
                    # ast.parse("import lmql.runtime.lmql_runtime as lmql"),
                    snf.ast(),
                    ast.Assign(
                        node.targets, 
                        ast.Call(ast.Name("LMQLExpr"), [value], [])
                    )
                ]), node)
        
        return node

def lmql_test(fct):
    source = inspect.getsource(fct)
    startline = inspect.getsourcelines(fct)[1]
    source = '\n'.join(source.splitlines()[1:])
    source = " \n" * startline + source

    bogus_query = LMQLQuery()
    bogus_query.scope = PromptScope()
    bogus_query.scope.defined_vars = set()
    expr_compiler = WhereClauseTransformation(bogus_query)
    compiler = LMQLExpressionCompiler(expr_compiler)

    m = ast.parse(source)
    m = compiler.visit(m)

    code = astunparse.unparse(m)

    global show_transformed
    if show_transformed: print(code.strip())
    
    recompiled = compile(code, fct.__code__.co_filename, 'exec')
    return types.FunctionType(recompiled.co_consts[0], fct.__globals__)

def fin(v):
    return (v, "fin")

def var(v):
    return (v, "var")

def inc(v):
    return (v, "inc")

def dec(v):
    return (v, "dec")

def run_all_tests(g):
    g = g.copy()
    num_errors = 0
    loop = asyncio.get_event_loop()

    for k in list(g.keys()):
        try:
            if k.startswith("test"): 
                print("Running", k, "." * (40 - len(k)), end=" ")
                
                if (type(g[k]) is LMQLQueryFunction or hasattr(g[k], "lmql_code")) and g[k].is_async:
                    loop.run_until_complete(g[k]())
                elif inspect.iscoroutinefunction(g[k]):
                    loop.run_until_complete(g[k]())
                else:
                    g[k]()
                termcolor.cprint("OK", "green")
        except AssertionError as e:
            num_errors += 1
            termcolor.cprint("FAILED", "red")
            print(e)

    # wait for all tasks to finish
    try:
        for t in asyncio.all_tasks(loop=loop):
            if t.done(): continue
            try:
                t.cancel()
                loop.run_until_complete(t)
            except asyncio.CancelledError:
                pass
        loop.close()
    except RuntimeError:
        pass

    if num_errors != 0: 
        print(num_errors, "test(s) failed.")
        sys.exit(1)
    else: 
        sys.exit(0)

def enable_show_transformed():
    global show_transformed
    show_transformed =True