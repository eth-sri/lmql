import lmql
import json
from lmql.tests.expr_test_utils import run_all_tests

@lmql.query
def test_curly_braces():
    '''lmql
    argmax 
        value = "[abc]"
        "{{ Say {value} 'this is a test':[RESPONSE] }}"
        assert context.prompt == "{ Say [abc] 'this is a test':\n\nThis is a test. }"
    from 
        "openai/text-ada-001" 
    where 
        len(TOKENS(RESPONSE)) < 10
    '''

@lmql.query
def test_curly_only():
    '''lmql
    argmax 
        "{{ Say }}"
        assert context.prompt == "{ Say }"
    from 
        "openai/text-ada-001" 
    '''


@lmql.query
def test_square_only():
    '''lmql
    argmax 
        "[[Say]]"
        assert context.prompt == "[Say]"
    from 
        "openai/text-ada-001" 
    '''

@lmql.query
def test_square_with_var_only():
    '''lmql
    argmax 
        "[[[Say]]]"
        assert context.prompt == "[Hello]"
    from 
        "openai/text-ada-001" 
    where
        Say == "Hello"
    '''

@lmql.query
def test_square_in_constraint():
    '''lmql
    argmax
        person = "test"
        "Hello {person}, my name is [NAME]. Nice to meet you!"
    from
        "openai/text-ada-001"
    where
        NAME in ["["]
    '''

@lmql.query
def test_json_decoding():
    '''lmql
    argmax 
        """
        Write a summary of Bruno Mars, the singer:
        {{
        "name": "[STRING_VALUE]",
        "age": [INT_VALUE],
        "top_songs": [[
            "[STRING_VALUE]",
            "[STRING_VALUE]"
        ]]
        }}
        """
        import json
        json.loads(context.prompt.split(":",1)[1])
    from
        "openai/text-davinci-003" 
    where
        STOPS_BEFORE(STRING_VALUE, '"') and INT(INT_VALUE) and len(TOKENS(INT_VALUE)) < 2
    '''

run_all_tests(globals())