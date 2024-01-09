---
title: 🌴 Packing List
---

Prompt construction and generation is implemented via expressive *Python control flow and string interpolation*.

%SPLIT%
```lmql
# top level strings are prompts
"My packing list for the trip:"

# use loops for repeated prompts
for i in range(4):
    # 'where' denotes hard constraints enforced by the runtime
    "- [THING] \n" where THING in \ 
        ["Volleyball", "Sunscreen", "Bathing Suit"]
```
%SPLIT%
```promptdown
My packing list for the trip:

- [THING| Volleyball]
- [THING| Bathing Suit]
- [THING| Sunscreen]
- [THING| Volleyball]
```
