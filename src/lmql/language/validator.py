from lmql.language.qstrings import qstring_to_stmts, TemplateVariable
from lmql.language.fragment_parser import LMQLQuery
import ast

class LMQLValidationError(Exception): ...

class QueryStringDistributionVarValidator(ast.NodeVisitor):
    """
    Transformes string expressions on statement level to model queries.
    """
    
    def __init__(self, query, variable_name):
        self.query = query
        self.distribution_variable = variable_name
        self.distribution_variable_used = False
    
    def validate(self):
        for p in self.query.prompt:
            self.visit(p)

    def visit_Expr(self, expr):
        if type(expr.value) is ast.Constant:
            self.check_Constant(expr.value)
        else:
            self.generic_visit(expr)
        return expr

    def check_Constant(self, constant):
        if type(constant.value) is not str: return constant
        qstring = constant.value
        # TODO: handle escaping more completely and gracefully
        qstring = qstring.replace("\n", "\\\\n")
        
        # get 
        for qstmt in qstring_to_stmts(qstring):
            if self.distribution_variable_used:
                raise LMQLValidationError("The distribution variable can only be used at the very end of the prompt.")
            if type(qstmt) is TemplateVariable:
                if qstmt.name == self.distribution_variable:
                    self.distribution_variable_used = True

class LMQLValidator:
    def validate(self, query: LMQLQuery):
        if query.distribution is not None:
            self.check_distribution_var_valid_position(query, query.distribution.variable_name)

    def check_distribution_var_valid_position(self, q: LMQLQuery, variable_name: str):
        QueryStringDistributionVarValidator(q, variable_name).validate()

