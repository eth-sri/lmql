from lmql.runtime.decoder_head import DecoderHead

class GroupByPostprocessor:
    def __init__(self):
        pass

    async def process(self, results, interpreter):
        raise NotImplementedError()