import lmql
from lmql.runtime.bopenai import get_stats

"""
Tests that back-to-back variables are cached correctly.
"""

@lmql.query
async def q():
    '''lmql
    argmax
        "1. Thought I believe in you\n"
        "2. Action I will help\n"
        "3. Thought This is good\n"
        "[NUM][MODE][CONTENT]" 
    from 
        # lmql.model("random", seed=123)
        lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded")
    where 
        MODE in [" Action", " Thought"] and STOPS_AT(CONTENT, "\n") and STOPS_AT(NUM, ".") and len(TOKENS(NUM)) < 4 and len(TOKENS(CONTENT)) < 16
    '''

with lmql.traced("back2back") as t:
    result: lmql.LMQLResult = lmql.main(q)
    assert len(result.variables["CONTENT"]) > 5, f"Expected CONTENT to be longer than 5 characters, got {str([result.variables['CONTENT']])}"

    cert = lmql.certificate(t)
    events = cert.asdict()["children"][0]["events"]

    generate_calls = [e for e in events if e['name'] == 'lmtp.generate']
    assert len(generate_calls) == 2, f"Expected 2 generate calls, got {len(generate_calls)}"