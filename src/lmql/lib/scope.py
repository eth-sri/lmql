from lib.errors import error
from parser.ast import FunctionCall, Identifier, Variable
from parser.ast import PromptInput, PromptVariable
from parser.ast import Query

class Scope:
    def __init__(self):
        self.names = {}

    def add(self, name, meaning):
        self.names[name] = meaning

    def has(self, name):
        return name in self.names

    def resolve(self, name):
        return self.names[name]

def scope(query):
    assert query.scope is None, "Cannot call scope() more than once on the same Query element."
    query.scope = Scope()

    # prompt first
    for l in query.prompt_clause:
        if type(l) is PromptInput:
            scope_expr(l.input, query)
        elif type(l) is PromptVariable:
            if query.scope.has(l.name):
                error("redeclaration of output variable {}.".format(l.name), l)

            var = Variable(l.name, "str")
            l.meaning = var
            query.scope.add(l.name, var)

    return query

def scope_expr(e, query):
    if type(e) is str:
        # nothing to scope in string prompts
        return
    elif type(e) is Identifier:
        if not query.scope.has(e.name):
            # automatically introduce input variables (user input fields)
            query.input_variables += [Variable(e.name, "str")]
            e.meaning = query.input_variables[-1]
            # error("failed to resolve variable {}".format(l.name), l)
        else:
            e.meaning = query.scope.resolve(e.name)
    elif type(e) is FunctionCall:
        if not query.scope.has(e.function_name):
            # automatically introduce input variables (user input fields)
            query.input_variables += [Variable(e.function_name, "function")]
            e.meaning = query.input_variables[-1]
            
            for a in e.args: scope_expr(a, query)
            # error("failed to resolve variable {}".format(l.name), l)
    else:
        error("{} expression is not supported as part of prompt".format(type(e)), e)