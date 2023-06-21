import lmql
from lmql.tests.expr_test_utils import run_all_tests


@lmql.query
async def test_q(actual_input: str = None):
    '''lmql
    a = 12

    def f(): return 12

    class A: pass

    argmax
        "Q: Hi {actual_input} {a}{f}{A}"
        for id in ['A', 'a', 'f']:
            assert locals().get(id) is None and globals().get(id) is not None, f"Global identifier {id} in local scope, or not in global scope. locals: {locals()}"
        assert "actual_input" in locals().keys(), f"Input variable actual_input not in local scope. locals: {locals()}"
        assert "actual_input" not in globals().keys(), f"Input variable actual_input not in global scope. locals: {locals()}"
    from 
        "openai/text-ada-001"
    '''

async def test_decode_clause_scoping():
    await lmql.run('''lmql
    argmax(n=n)
        "Q: Hi {n}. A: [WHO]"
        assert "n" in locals().keys(), f"Input variable n not captured by scope"
    from 
        "openai/text-ada-001" 
    where
        len(TOKENS(WHO)) < 10
    '''
    , n=1)


async def test_output_vars():
    @lmql.query
    async def q():
        '''lmql
        argmax "Q: Hi {n}. A: [WHO]" from "openai/text-ada-001" where len(TOKENS(WHO)) < 10
        '''
    assert q.output_variables == ['WHO'], f"Expected output variables to be ['WHO'], got {q.output_variables}"

async def test_python_capture():
    def f(a): return 12 + a

    @lmql.query
    async def q():
        '''lmql
        argmax 
            "Q: Hi {f(1)}. A: [WHO]" 
            assert context.prompt.startswith("Q: Hi 13")
        from 
            "openai/text-ada-001" 
        where 
            len(TOKENS(WHO)) < 10
        '''
    await q()

run_all_tests(globals())
