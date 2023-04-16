from lmql.runtime.program_state import ProgramState
from lmql.runtime.multi_head_interpretation import InterpreterCall

class LMQLContextAPI:
    def __init__(self, program_variables, interpreter):
        self.program_variables: ProgramState = program_variables
        self.interpreter = interpreter

    async def json(self):
        return self.program_variables

    # LMQL runtime API

    async def get_var(self, name):
        return self.program_variables.get_program_value(name)

    async def query(self, qstring):
        return InterpreterCall(qstring, loc=None)

    async def set_model(self, model_name):
        self.interpreter.set_model(model_name)

    async def set_decoder(self, method, **kwargs):
        self.interpreter.set_decoder(method, **kwargs)

    async def set_where_clause(self, where):
        self.interpreter.set_where_clause(where)

    async def get_all_vars(self):
        return self.program_variables.variable_values.copy()

    async def set_distribution(self, distribution_variable, values):
        self.interpreter.set_distribution(distribution_variable, values)

    async def get_return_value(self, *args):
        return LMQLResult(self.prompt, await self.get_all_vars(), self.interpreter.distribution_variable, self.interpreter.distribution_values)
