---
title: ⛓️ Constrained LLMs
---

LMQL's support for constrained generation enables robust interfacing, to integrate LLMs safely into your applications.<a href="../../guide/constraints.html">Learn More →</a>

%SPLIT%
```lmql
# top-level strings are prompts
"Tell me a joke:\n"

# use 'where' constraints to control and restrict generation
"Q:[JOKE]\n" where len(JOKE) < 120 and STOPS_AT(JOKE, "?")

"A:[PUNCHLINE]\n" where \ 
    STOPS_AT(PUNCHLINE, "\n") and len(TOKENS(PUNCHLINE)) > 1
```
%SPLIT%
```promptdown
Tell me a joke:

Q: [JOKE| What did the fish say when it hit the wall?]
A: [PUNCHLINE| Dam!]
```