---
title: 
template: code
---

```lmql
controls::

@lmql.query
def meaning_of_life():
    '''lmql
    # top-level strings are prompts
    "Q: What is the answer to life, the \
     universe and everything?"

    # generation via (constrained) variables
    "A: [ANSWER]" where \
        len(ANSWER) < 120 and STOPS_AT(ANSWER, ".")

    # results are directly accessible
    print("LLM returned", ANSWER)

    # use typed variables for guaranteed 
    # output format
    "The answer is [NUM: int]"

    # query programs are just functions 
    return NUM
    '''

# so from Python, you can just do this
meaning_of_life() # 42
```

<br/>
<center style="font-size: 10pt">

Created by the [SRI Lab](http://sri.inf.ethz.ch/) @ ETH Zurich and [contributors](https://github.com/eth-sri/lmql).

<br/>

<div class="github-star">
    <a class="github-button" href="https://github.com/eth-sri/lmql" data-color-scheme="light" data-show-count="true" aria-label="Star LMQL on GitHub">Star</a>
</div>

</center>
