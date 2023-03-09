class ProgramState:
    def __init__(self, runtime=None):
        self.variable_values = {}
        self.variable_diffs = {}
        self.variable_scores = {}
        self.variable_monotonicity = {}

        self.runtime = runtime

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

    def set(self, name, value, scores=None, diff=None, montonicity="var"):
        self.variable_values[name] = value
        self.variable_diffs[name] = diff
        self.variable_scores[name] = scores
        self.variable_monotonicity[name] = montonicity

    def get(self, name, default=None):
        return self.variable_values.get(name, default)
    
    def get_diff(self, name, default=None):
        return self.variable_diffs.get(name, default)

    def final(self, name):
        return self.variable_monotonicity.get(name, "var")

    def copy(self):
        s = ProgramState()
        s.variable_values = self.variable_values.copy()
        s.variable_monotonicity = self.variable_monotonicity.copy()
        s.variable_diffs = self.variable_diffs.copy()
        s.variable_scores = self.variable_scores.copy()
        s.runtime = self.runtime
        return s