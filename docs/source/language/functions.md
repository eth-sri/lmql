# Nested Queries <span class="tag" data-tag-name="functions">NEW</span>

<div class="subtitle">Modularize your query code with nested prompting.</div>

*Nested Queries* allow you to execute a query function within the context of another. By nesting multiple query functions, you can build complex programs from smaller, reusable components. For this, LMQL applies the idea of [procedural programming](https://en.wikipedia.org/wiki/Procedural_programming) to prompting.

To better understand this concept, let's take a look at a simple example:

```{lmql}
name::prompt-function

@lmql.query
def chain_of_thought():
    '''lmql
    "A: Let's think step by step.\n [REASONING]"
    "Therefore the answer is[ANSWER]" where STOPS_AT(ANSWER, ".")
    return ANSWER.strip()
    '''

"Q: It is August 12th, 2020. What date was it \
    100 days ago? [ANSWER: chain_of_thought]"
```

Here, the placeholder variable `ANSWER` is annotated with a reference to query function `chain_of_thought`. This means a nested instantiation of query function `chain_of_thought` will be used to generate the value for `ANSWER`.

To understand how this behaves at runtime, consider the execution trace of this program:

```{promptdown}
animate::true
min-height::10em
### Model Output
![Q: It is August 12th, 2020. What date was it 100 days ago?]
[@wait|800]
[@begin|incontext][chain_of_thought|A: Let's think step by step.]
[@wait|800][REASONING|100 days ago would be May 4th, 2020.][Therefore the answer is][@end|incontext][ANSWER|May 4th, 2020]
[@wait|800]
[@fade|incontext]
[@wait|800]
[@hide|incontext]
[:replay]
```

> You can press *Replay* to re-run the animation.

To generate `ANSWER`, the additional prompt and constraints defined by `chain_of_thought` are inserted into our main query context. However, after `ANSWER` has been generated, the additional instructions are removed from the trace, leaving only the return value of the nested query call. This mechanic is comparable to a function's stack frame in procedural programming.

Nesting allows you to use variable-specific instructions that are only locally relevant, without interfering with other parts of the program, encapsulating the logic of your prompts into reusable components.

### Parameterized Queries

You can also pass parameters to nested queries, allowing you to customize their behavior:

```{lmql}
name::prompt-function-params

@lmql.query
def one_of(choices: list):
    '''lmql
    "Among {choices}, what do you consider \
    most likely? [ANSWER]" where ANSWER in choices
    return ANSWER
    '''

"Q: What is the capital of France? \
[ANSWER: one_of(['Paris', 'London', 'Berlin'])]"
```

```{promptdown}
animate::true
min-height::10em

### Model Output
![Q: What is the capital of France?]
[@wait|800]
[@begin|incontext][one_of|Among ['Paris', 'London', 'Berlin'], what do you consider most likely?][@end|incontext]
[@wait|800][ANSWER|Paris]
[@wait|800]
[@fade|incontext]
[@wait|800]
[@hide|incontext]
[:replay]
```

For instance, here we employ `one_of` to generate the answer to a multiple-choice question. The `choices` are passed as a parameter to the nested query, allowing us to reuse the same code for different questions.

### Multi-Part Programs

You can also use multiple nested queries in sequence, allowing you to repeatedly inject instructions into your prompt without interfering with the overall flow:

```{lmql}
name::dateformat

@lmql.query
def dateformat():
    '''lmql
    "(respond in DD/MM/YYYY) [ANSWER]"
    return ANSWER.strip()
    '''

"Q: When was Obama born? [ANSWER: dateformat]\n"
"Q: When was Bruno Mars born? [ANSWER: dateformat]\n"
"Q: When was Dua Lipa born? [ANSWER: dateformat]\n"

"Out of these, who was born last?[LAST]"
```

```{promptdown}
animate::true
min-height::14em
### Model Output
![Q: When was Obama born?]
[@wait|200]
[@begin|incontext][dateformat|(respond in DD/MM/YYYY)][@end|incontext]
[@wait|200][ANSWER|04/08/1961]
[@wait|200]
[@fade|incontext]
[@wait|200]
[@hide|incontext]
[@wait|200]
![Q: When was Bruno Mars born?]
[@wait|200]
[@begin|incontext1][dateformat|(respond in DD/MM/YYYY)][@end|incontext1]
[@wait|200][ANSWER|08/10/1985]
[@wait|200]
[@fade|incontext1]
[@wait|200]
[@hide|incontext1]
[@wait|200]
![Q: When was Dua Lipa born?]
[@wait|200]
[@begin|incontext2][dateformat|(respond in DD/MM/YYYY)][@end|incontext2]
[@wait|200][ANSWER|22/08/1995]
[@wait|200]
[@fade|incontext2]
[@wait|200]
[@hide|incontext2]
[@wait|200]

[Out of these, who was born last?][LAST|Dua Lipa]
[:replay]
```

We instruct the model to use a specific date format when answering our initial questions. Because of the use of `dateformat` as a nested function, the instructions are only temporarily included, once per generated answer, and removed before moving on to the next question.

Once we have generated all intermediate answers, we query the LLM to compare the individual dates and determine the latest one, where this last query is not affected by the instructions of `dateformat`.

## Return Values

If a query function does _not_ return a value, calling it as nested function does _not_ remove the inserted instructions after execution. The effect of a nested function without return value therefore corresponds to a macro expansion, as shown below:

This can be helpful when you want to use a fixed template in several locations, e.g. for list items. Further, as shown below, a nested function can also be parameterized to customize its behavior:

```{lmql}
name::incontext-no-return

@lmql.query
def items_list(n: int):
    '''lmql
    for i in range(n):
        "-[ITEM]" where STOPS_AT(ITEM, "\n")
    '''

"A list of things not to forget to pack for your \
 next trip:\n[ITEMS: items_list(4)]"
```

```{promptdown}
animate::true
min-height::10em

![A list of things not to forget to pack for your next trip:]
![ITEM|- Passport]
![ITEM|- Toothbrush]
![ITEM|- Phone charger]
![ITEM|- Sunscreen]
```

## Nested Queries in Python

To use nested queries from a Python context, you can just reference one `@lmql.query` function from another.

```python

@lmql.query
def dateformat():
    '''lmql
    "(respond in DD/MM/YYYY)[ANSWER]"
    return ANSWER.strip()
    '''

@lmql.query
def main_query():
    '''lmql
    "Q: It is August 12th, 2020. What date was it \
    100 days ago? [ANSWER: dateformat]"
    '''
```

Here, `main_query` references `dateformat` as a nested query, where both functions are defined on the top level of the same file. However, you can also import and reuse query code from other files, as long as they are accessible from the scope of you main query function. Using this ability you can write libraries of reusable query functions to be used across your application or even by other users.