"""
Minimal LMQL Chat endpoint server, that serves a given LMQL file as a chat application.

See assets/ for the client implementation.
"""
from .output import *

"""
Decorator to mark user-facing messages as "[@message MESSAGE]" in Chat queries

See 'MessageDecorator' for the actual implementation.
"""
message = MessageDecorator()

def chatserver(*args, **kwargs):
    """
    Constructs a chatserver instance with the given arguments.
    """
    from .chatserver import ChatServer
    
    return ChatServer(*args, **kwargs)