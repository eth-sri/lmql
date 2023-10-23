import asyncio

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
        error = None
        
        while True:
            try:
                item = await asyncio.wait_for(self.aiterator.__anext__(), timeout=60)
                yield item
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                error = TimeoutError("Timeout while waiting for stream {}".format(self.stream_id))
        
        if error is not None:
            raise error