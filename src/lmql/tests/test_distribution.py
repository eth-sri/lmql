import lmql
import numpy as np

from lmql.tests.expr_test_utils import run_all_tests


@lmql.query(model=lmql.model("random", seed=123))
def test_distribution_no_vars():
    '''lmql
    argmax
        "Select something"
        "Choice: [CLS]"
    distribution
        CLS in [" positive", " neutral", " negative"]
    '''

if __name__ == "__main__":
    run_all_tests(globals())