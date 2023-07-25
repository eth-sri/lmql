import lmql
from lmql.tests.expr_test_utils import run_all_tests

m = lmql.model("gpt2", inprocess=True)

@lmql.query
def test_model_reference():
    '''lmql
    import lmql

    argmax(chunk_timeout=10.0)
        """Hello[WHO]"""
    from
        m
    where
        STOPS_AT(WHO, "\n") and len(TOKENS(WHO)) < 10
    '''

@lmql.query
def test_local_string():
    '''lmql
    import lmql

    argmax(chunk_timeout=10.0)
        """Hello[WHO]"""
    from
        "local:gpt2"
    where
        STOPS_AT(WHO, "\n") and len(TOKENS(WHO)) < 10
    '''

m2 = lmql.model("gpt2", cuda=True, inprocess=True)

@lmql.query
def test_model_reference_cuda():
    '''lmql
    import lmql

    argmax(chunk_timeout=10.0)
        """Hello[WHO]"""
    from
        m2
    where
        STOPS_AT(WHO, "\n") and len(TOKENS(WHO)) < 10
    '''

@lmql.query(model=m2)
def test_model_reference_cuda_decorator():
    '''lmql
    "Hello[WHO]" where STOPS_AT(WHO, "\n") and len(TOKENS(WHO)) < 10
    '''


if __name__ == "__main__":
    run_all_tests(locals())