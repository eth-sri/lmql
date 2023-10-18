class LMTPStreamHandle:
    """
    Stream of future LMTP messages from the server,
    identified by a stream_id.
    """
    def __init__(self, stream_id, aiterator, client):
        self.stream_id = stream_id
        self.aiterator = aiterator
        self.client = client
    
    async def stream(self):
        async for item in self.aiterator:
            yield item