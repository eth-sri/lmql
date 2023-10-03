import lmql.version as version_info

"""
lmql.

A query language for language models.
"""

__version__ = version_info.version
__author__ = 'Luca Beurer-Kellner, Marc Fischer and Mark Mueller'
__email__ = "luca.beurer-kellner@inf.ethz.ch"
__license__ = "Apache 2.0"

# public LMQL API like lmql.query, lmql.run, lmql.LLM, lmql.model, lmql.generate, lmql.score etc.
from lmql.api import *

# language support

# runtime
import lmql.runtime.lmql_runtime as lmql_runtime
import lmql.runtime.lmql_runtime as runtime_support

# LMQL variable decorators
import lmql.runtime.decorators as decorators

# output and result types
from lmql.runtime.interpreter import LMQLResult
from lmql.runtime.output_writer import headless, printing, silent, stream

# re-export lmql runtime functions
from lmql.runtime.lmql_runtime import (LMQLQueryFunction, compiled_query, tag)

# event loop utils
from lmql.runtime.loop import main