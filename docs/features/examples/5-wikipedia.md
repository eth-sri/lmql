---
title: 🌎 Tool Augmentation
---

LMQL supports *arbitrary Python function calls during generation*, enabling seamless integration with external tools and APIs, augmenting the model's capabilities.

%SPLIT%
```lmql
# define or import an external function
async def wikipedia(q): ...

# pose a question
"Q: From which countries did the Norse originate?\n"

# invoke 'wikipedia' function during reasoning
"Action: Let's search Wikipedia for the \
 term '[TERM]\n" where STOPS_AT(TERM, "'")

# seamlessly call it *during* generation
result = await wikipedia(TERM)
"Result: {result}\n"

# generate final response using retrieved data
"Final Answer:[ANSWER]"
```
%SPLIT%
```promptdown
Q: From which countries did the Norse originate?

Action: Let's search Wikipedia for the term [TERM| 'Norse']
Result: (Norse is a demonym for Norsemen, a Medieval North Germanic ethnolinguistic group ancestral to modern Scandinavians, defined as speakers of Old Norse from about the 9th to the 13th centuries.)

Final Answer: [ANSWER| The Norse originated from Scandinavia.]
```