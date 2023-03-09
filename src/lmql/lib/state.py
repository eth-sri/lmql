class ProgramState:
    def __init__(self):
        self.variables = {}
        self.variables_by_str = {}

        self.globals = {}

    def set(self, var, value):
        self.variables[var] = value
        self.variables_by_str[var.name] = var

    def get(self, var):
        return self.variables[var]
    
    def resolve(self, name: str):
        v = self.variables_by_str[name]
        return self.variables[v]

    def add_global(self, name, value):
        self.globals[name] = value
