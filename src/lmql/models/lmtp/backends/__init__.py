# always available
import lmql.models.lmtp.backends.random_model

# only available with 'transformers' package
try:
    import transformers
    import lmql.models.lmtp.backends.transformers
except:
    pass

from lmql.models.lmtp.backends.basemodel import LMTPModel