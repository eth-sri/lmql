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
        "openai/text-davinci-003" 
    where 
        MODE in [" Action", " Thought"] and STOPS_AT(CONTENT, "\n") and STOPS_AT(NUM, ".")
    '''

result = lmql.main(q)[0]
assert len(result.variables["CONTENT"]) > 5, f"Expected CONTENT to be longer than 5 characters, got {result.variables['CONTENT']}"
stats = get_stats()
requests = str(stats).split(",")[0].split(":")[1].strip()
assert requests == "2 requests", f"Expected query to need 2 requests, got {requests}"