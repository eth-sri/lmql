import lmql
from lmql.tests.expr_test_utils import run_all_tests

@lmql.query
async def test_legacy_model():
    '''lmql
    import lmql

    argmax(chunk_timeout=10.0, backend="legacy")
        """Hello[WHO]"""
    from
        "local:facebook/opt-350m"
    where
        STOPS_AT(WHO, "\n") and len(TOKENS(WHO)) < 10
    '''

run_all_tests(locals())