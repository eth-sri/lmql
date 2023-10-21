# always available
from lmql.models.lmtp.backends.lmtp_model import LMTPModel

# uniform random model
import lmql.models.lmtp.backends.random_model

# only available with 'transformers' package
try:
    import transformers
    import lmql.models.lmtp.backends.transformers_model
except:
    pass

# only available with llama.cpp python bindings
@LMTPModel.register("llama.cpp", module_dependencies=["llama_cpp"])
def _llama_cpp_importer():
    import lmql.models.lmtp.backends.llama_cpp_model
