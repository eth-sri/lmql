class GroupByPostprocessor:
    def __init__(self):
        pass

    async def process(self, results, interpreter):
        raise NotImplementedError()