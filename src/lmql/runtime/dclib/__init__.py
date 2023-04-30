from .dclib_global import *
from .dclib_array import *
from .dclib_model import *
from .dclib_seq import *
from .dclib_cache import *

class _Decoders: pass
_Decoders.registry = {}

def get_decoder(name):
    return _Decoders.registry[name]

def get_all_decoders():
    return _Decoders.registry.keys()

# decoder decorator which keeps track of all decoders by name
def decoder(fct, name=None):
    if name is None: 
        name = fct.__name__
    _Decoders.registry[name] = fct
    return fct