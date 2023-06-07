import lmql

@lmql.query
async def positional_only(s: str):
    '''lmql
    argmax
        return s
    from
        "chatgpt"
    where
        STOPS_AT(ANSWER, "test") and STOPS_AT(OTHER, "test")
    '''

CONSTANT = 123

@lmql.query
async def noinput_but_specified():
    '''lmql
    argmax
        return s, CONSTANT
    from
        "chatgpt"
    '''

MODEL = "chatgpt"
@lmql.query
async def external_model():
    '''lmql
    argmax
        "Hi[SEP]"
    from
        MODEL
    '''


async def test_var_errors():
    try:
        await positional_only("test")
        assert False, "Expected error"
    except TypeError as e:
        assert "Failed to resolve variables in LMQL query: 'ANSWER', 'OTHER'" in str(e), f"Expected different error, got {e}"

    try:
        await noinput_but_specified()
        assert False, "Expected error"
    except TypeError as e:
        assert "Failed to resolve variable 's'" in str(e), f"Expected different error, got {e}"

    # this should work
    await noinput_but_specified(s="test")

    # external model should work
    await external_model()