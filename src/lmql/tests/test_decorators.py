import lmql

class DecoratorLog:
    def __init__(self):
        self.pre_input = None
        self.stream_input = None
        self.post_input = None
    
global decorator_log
decorator_log = DecoratorLog()  

@lmql.decorators.pre
def pre(variable):
    global decorator_log
    decorator_log.pre_input = variable
    # can intercept generation of variable
    return variable 

@lmql.decorators.streaming
def stream(s, context):
    global decorator_log
    decorator_log.stream_input = s
    # streams during generation of variable
    pass

def post(value):
    # postprocesses value of variable
    global decorator_log
    decorator_log.post_input = value
    return value.replace("This", "Tthhiiss")

@lmql.query
def test_decorators():
    '''lmql
    argmax
        "Say 'this is a test':\n[@post @stream @pre RESPONSE]"

        assert decorator_log.pre_input.name == "RESPONSE", "expected pre_input to be 'RESPONSE' but got {}".format(decorator_log.pre_input)
        assert decorator_log.stream_input == "AME's barriers equality sea36 again disinfectGet", "expected stream_input to be 'RESPONSE' but got {}".format(decorator_log.stream_input)
        assert decorator_log.post_input == "AME's barriers equality sea36 again disinfectGet", "expected post_input to be 'AME's barriers equality sea36 again disinfectGet' but got {}".format(decorator_log.post_input)
    from 
        lmql.model("random", seed=123)
    where 
        len(TOKENS(RESPONSE)) < 10
    '''

@lmql.query(model=lmql.model("random", seed=123))
def test_inner_decorator():
    '''lmql
    log = DecoratorLog()

    def f(s):
        log.post_input = s
        return 12

    "Say 'this is a test':\n[@f RESPONSE]" where len(TOKENS(RESPONSE)) < 10

    # make sure program value is correct
    assert RESPONSE == 12, "expected program value of RESPONSE to be 12 but got {}".format(RESPONSE)
    
    # make sure rewrite works according to postprocessing semantics
    assert context.prompt == "Say 'this is a test':\n12", "expected prompt to be 'Say 'this is a test':\\n12' but got '{}'".format([context.prompt])

    assert log.post_input == "AME's barriers equality sea36 again disinfectGet", "expected post_input to be 'AME's barriers equality sea36 again disinfectGet' but got '{}'".format(log.post_input)
    '''


@lmql.query(model=lmql.model("random", seed=123))
def test_streaming_decorator():
    '''lmql
    log = DecoratorLog()
    log.stream_input = []

    @lmql.decorators.streaming
    def f(s, context):
        log.stream_input += [s]

    "Say 'this is a test':\n[@f RESPONSE]" where len(TOKENS(RESPONSE)) < 10

    assert log.stream_input == ['', '', 'AME', "AME's", "AME's barriers", "AME's barriers equality", "AME's barriers equality sea", "AME's barriers equality sea36", "AME's barriers equality sea36 again", "AME's barriers equality sea36 again disinfect", "AME's barriers equality sea36 again disinfectGet", "AME's barriers equality sea36 again disinfectGet"], "expected incremental stream of RESPONSE to be decorator input over time but got '{}'".format(log.stream_input)
    '''



@lmql.query(model=lmql.model("random", seed=123))
def test_pre_decorator():
    '''lmql
    log = DecoratorLog()
    log.stream_input = []

    @lmql.decorators.pre
    def f(variable):
        return "Fixed Value"

    "Say 'this is a test':\n[@f RESPONSE]" where len(TOKENS(RESPONSE)) < 10

    assert RESPONSE == "Fixed Value", "expected RESPONSE to be 'Fixed Value' but got '{}'".format(RESPONSE)
    '''


if __name__ == "__main__":
    from lmql.tests.expr_test_utils import run_all_tests
    run_all_tests(globals())