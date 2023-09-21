class ProgramState:
    """
    Program state tracked by the interpreter during program execution.
    """
    def __init__(self, prompt, runtime=None):
        self.variable_values = {}
        # postprocessed, converted variable values if not just str (e.g. objects, int)
        self.variable_program_values = {}
        self.variable_diffs = {}
        self.variable_scores = {}
        self.variable_monotonicity = {}

        # python scope of local variables (also user-defined ones)
        self.python_scope = {}

        self.runtime = runtime
        self.subinterpreter_results = {}
        self.prompt = prompt

    async def json(self):
        def json_value(k):
            fin = self.variable_monotonicity.get(k, "var")
            # do not include diff and score for now
            return fin + "(\"" + str(self.variable_values[k]) + "\")"
        return {k: json_value(k) for k in self.variable_values.keys()}

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def set(self, name, value, program_value=None, scores=None, diff=None, montonicity="var"):
        self.variable_values[name] = value
        self.variable_program_values[name] = program_value if program_value is not None else value
        self.variable_diffs[name] = diff
        self.variable_scores[name] = scores
        self.variable_monotonicity[name] = montonicity

    def get(self, name, default=None):
        return self.variable_values.get(name, default)

    def get_program_value(self, name, default=None):
        return self.variable_program_values.get(name, default)
    
    def get_diff(self, name, default=None):
        return self.variable_diffs.get(name, default)

    def final(self, name):
        return self.variable_monotonicity.get(name, "var")

    def copy(self):
        s = ProgramState(self.prompt)
        s.variable_values = self.variable_values.copy()
        s.variable_program_values = self.variable_program_values.copy()
        s.variable_monotonicity = self.variable_monotonicity.copy()
        s.variable_diffs = self.variable_diffs.copy()
        s.variable_scores = self.variable_scores.copy()
        s.runtime = self.runtime
        s.python_scope = self.python_scope
        return s