class QueryBuilder:
    def __init__(self):
        self.decoder = None
        self.prompt = None
        self.model = None
        self.where = None
        self.distribution_expr = None

    def set_decoder(self, decoder='argmax', **kwargs):
        if decoder not in ['argmax', 'sample', 'beam', 'beam_var', 'var', 'best_k']:
            raise ValueError(f"Invalid decoder: {decoder}")
        self.decoder = (decoder, kwargs)
        return self

    def set_prompt(self, prompt="What is the capital of France? [ANSWER]"):
        self.prompt = prompt
        return self

    def set_model(self, model="gpt2"):
        self.model = model
        return self

    def set_where(self, where="len(TOKENS(ANSWER)) < 10"):
        """
        Add a where clause to the query
        If a where clause already exists, the new clause is appended with an 'and'
        If the user wants to use 'or', they need to put or in the where clause
        such as: "len(TOKENS(ANSWER)) < 10 or len(TOKENS(ANSWER)) > 2"
        """
        self.where = where if self.where is None else f"{self.where} and {where}"
        return self

    def set_distribution(self, variable="ANSWER", expr='["A", "B"]'):
        self.distribution_expr = (variable, expr)
        return self

    def build(self):
        components = []

        if self.decoder:
            decoder_str = self.decoder[0]
            if self.decoder[1]:  # If keyword arguments are provided
                decoder_str += f"({self.decoder[1]})"
            components.append(decoder_str)

        if self.prompt:
            components.append(f'"{self.prompt}"')

        if self.model:
            components.append(f'from "{self.model}"')

        if self.where:
            components.append(f'where {self.where}')

        if self.distribution_expr:
            variable, expr = self.distribution_expr
            components.append(f'distribution {variable} in {expr}')

        return ' '.join(components)

