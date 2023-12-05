import lmql
from lmql.tests.expr_test_utils import run_all_tests

async def test_stopping_overlap_before():
    @lmql.query
    async def q():
        '''lmql
        sample(temperature=0.8, max_len=64)
            "The movie review in positive sentiment is: [OUTPUT]"
        FROM
            lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded")
        WHERE
            STOPS_BEFORE(OUTPUT, "\n") and STOPS_BEFORE(OUTPUT, "n") and len(TOKENS(OUTPUT)) < 10
        '''
    (await q())[0]

@lmql.query
async def test_stopping_double_match():
    '''lmql
    argmax 
        '{{"1","2","3","[COMPL]}}'
        assert COMPL == '4"', "Expected COMPL to be '4\"', but was " + str([COMPL])
    from 
        lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded") 
    where 
        len(TOKENS(COMPL)) < 10 and STOPS_AT(COMPL, '"')
    '''

@lmql.query
async def test_stopping_double_match_before():
    '''lmql
    argmax 
        '{{"1","2","3","[COMPL]"}}'
        assert COMPL == '4', "Expected COMPL to be '4', but was " + str([COMPL])
    from 
        lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded") 
    where 
        len(TOKENS(COMPL)) < 10 and STOPS_BEFORE(COMPL, '"')
    '''

@lmql.query
async def test_stopping_single_match():
    '''lmql
    argmax 
        """
        My name is Peter. In JSON:
        {{
            "name": "[COMPL]
        }}
        """
        assert COMPL == 'Peter"', "Expected COMPL to be 'Peter\"', but was " + str([COMPL])
    from 
        lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded") 
    where 
        STOPS_AT(COMPL, '"')
    '''

@lmql.query
async def test_conditional_stopping():
    '''lmql
    argmax 
        "The movie review in positive sentiment is: [OUTPUT]"
        assert OUTPUT.count("review") == 2
    from 
        lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded") 
    where 
        len(TOKENS(OUTPUT)) > 21 and STOPS_AT(OUTPUT, "review")
    '''

@lmql.query
async def test_conditional_or_stopping():
    '''lmql
    argmax 
        "The movie review in positive sentiment is: [OUTPUT]"
        assert OUTPUT.count("review") == 1
    from 
        lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded") 
    where 
        len(TOKENS(OUTPUT)) > 10 or STOPS_AT(OUTPUT, "review")
    '''

@lmql.query
async def test_double_stop_rewrite():
    '''lmql
    argmax 
        "The movie review in positive sentiment is: [OUTPUT] Here"
        assert OUTPUT.endswith("5/5.")
    from 
        lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded") 
    where 
        STOPS_BEFORE(OUTPUT, " ") and STOPS_AT(OUTPUT, "Unter")
    '''

@lmql.query
async def test_double_stop_rewrite_space():
    '''lmql
    argmax 
        "The movie review in positive sentiment is: [OUTPUT] Here"
        assert OUTPUT.endswith(" ")
    from 
        lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded") 
    where 
        STOPS_AT(OUTPUT, " ") and STOPS_AT(OUTPUT, "re")
    '''

@lmql.query
async def test_stop_should_not_postprocess_if_sc_not_satisfied():
    '''lmql
    argmax 
        "A good movie review:[REVIEW] "
        assert REVIEW.endswith("vendors"), "Expected REVIEW to end with 'vendors', but was " + str([REVIEW])
    from 
        lmql.model("random", seed=123)
    where
        len(TOKENS(REVIEW)) > 10 and STOPS_AT(REVIEW, "exempted") and STOPS_AT(REVIEW, "vendors")
    '''

@lmql.query
async def test_stop_before_should_not_postprocess_if_sc_not_satisfied():
    '''lmql
    argmax 
        "A good movie review:[REVIEW] "
        assert REVIEW.endswith("vendors"), "Expected REVIEW to end with 'vendors', but was " + str([REVIEW])
    from 
        lmql.model("random", seed=123)
    where
        len(TOKENS(REVIEW)) > 10 and STOPS_BEFORE(REVIEW, "exempted") and STOPS_AT(REVIEW, "vendors")
    '''

@lmql.query
async def test_stop_overlapping_before():
    '''lmql
    argmax
        """{{
            "first_name": "Bruno", 
            "last_name": "Mars", 
            "birthday": "1985-10-0", 
            "age": 32, 
            "hobby": [[
                "sing", 
                "dance"
            ]], 
            "address": {{
                "street_address": "12345", 
                "city": "New York", 
                "state": "NY", 
                "country":"US"
            }},
            # the 2 most popular songs
            """
        '"songs":[[\n        "[GEN_STR]' where STOPS_BEFORE(GEN_STR, ',') and STOPS_BEFORE(GEN_STR, '"') and STOPS_BEFORE(GEN_STR, ']') and len(TOKENS(GEN_STR)) < 10 and GEN_STR == 'abc",'
        assert GEN_STR == "abc", "Expected just 'abc', but got {}".format(str([GEN_STR])[1:-1])
    from 
        lmql.model("random", seed=123)
    '''

if __name__ == "__main__":
    run_all_tests(globals())