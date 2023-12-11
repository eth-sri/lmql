# Tool Augmentation

<div class="subtitle">Augment LLM reasoning with Python tool integration</div>

LMQL is a superset of Python and thus query programs can incorporate arbitrary Python constructs including function calls.
For instance, below, we ask the model for a simple math problem and then use Python's `eval` function to evaluate the solution.

```{lmql}
name::simple_math

# generates an arithmetic expression
"A simple math problem for addition (without solution, \
    without words): [MATH]" where STOPS_BEFORE(MATH, "=")

# evaluate the expression and feed it back into the prompt
"= {eval(MATH.strip())}"
```
```promptdown
A simple math problem for addition (without solution, without words):
[MATH| 7 + 8 =] 15
```



Here, similar to a python [f-string](https://peps.python.org/pep-0498), we use the `{...}` syntax to re-insert the result of the `eval` function into the prompt. This allows us to augment the reasoning capabilities of the large language model with a simple calculator.

::: warning
While `eval` is handy for the examples in this section and allows to perform simple math, generally it can pose a security risk and should not be used in production.
:::

## Calculator
Building on the previous example, we can now create an improved calculator that can handle more complex expressions:

```lmql
import re
from lmql.demo import gsm8k_samples

def calc(expr):
      expr = re.sub(r"[^0-9+\-*/().]", "", expr)
      return eval(expr)

QUESTION = "Josh decides to try flipping a house. \
He buys a house for $80,000 and then puts in $50,000 in repairs. \
This increased the value of the house by 150%. \
How much profit did he make?"

# insert few shot demonstrations
"{gsm8k_samples()}"

# prompt template
"Q: {QUESTION}\n"
"Let's think step by step.\n"

# reasoning loop
for i in range(4):
    "[REASON_OR_CALC]" \
        where STOPS_AT(REASON_OR_CALC, "<<") and \
              STOPS_AT(REASON_OR_CALC, "So the answer")
    
    if REASON_OR_CALC.endswith("<<"):
        " [EXPR]" where STOPS_AT(EXPR, "=")
        # invoke calculator function
        " {calc(EXPR)}>>"
    elif REASON_OR_CALC.endswith("So the answer"):
        break

# produce the final answer
"is[RESULT]"
```
```promptdown
Q: Josh decides to try flipping a house.  He buys a house for $80,000 and then puts in $50,000 in repairs.  This increased the value of the house by 150%.  How much profit did he make?

Let's think step by step.
[REASON_OR_CALC|Josh bought the house for $80,000 and put in $50,000 in repairs.
The value of the house increased by 150%, so the new value of the house is $80,000 + 150% of $80,000 = &lt;&lt;] [EXPR|80,000 + (80,000*1.5) =] 200000.0>> 
[REASON_OR_CALC|The profit Josh made is the difference between the new value of the house and the amount he spent on it, which is $200,000 - $80,000 - $50,000 = &lt;&lt;] [EXPR|200,000 - 80,000 - 50,000 =] 70000>> [REASON_OR_CALC| $70,000.
So the answer] is [RESULT|$70,000.]
```

Here, we define a function `calc` that leverages the build-in `re` library for regular expressions, to strip the input of any non-numeric characters before calling `eval`.

Further, we use a function `gsm8k_samples` that returns a few-shot samples for the `gsm8k` dataset, priming the model on the correct form of tool use.

## Beyond Calculators

**Wikipedia Search** Function use is not limited to calculators. In the example below we show how text retrieval, using Python's [`async`/`await` syntax](https://docs.python.org/3/library/asyncio.html), can be used to augment the reasoning capabilities of the large language model. 

```lmql
async def wikipedia(q):
   from lmql.http import fetch
   try:
      q = q.strip("\n '.")
      pages = await fetch(f"https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro&explaintext&redirects=1&titles={q}&origin=*", "query.pages")
      return list(pages.values())[0]["extract"][:280]
   except:
      return "No results"

# ask a question
"Q: From which countries did the Norse originate?\n"

# prepare wikipedia call
"Action: Let's search Wikipedia for the term '[TERM]\n" where STOPS_AT(TERM, "'")
result = await wikipedia(TERM)

# feed back result
"Result: {result}\n"

# generate final response
"Final Answer:[ANSWER]"
```
```promptdown
Q: From which countries did the Norse originate?
Action: Let's search Wikipedia for the term '[TERM| Norse]'.
Result: Norse is a demonym for Norsemen, a Medieval North Germanic ethnolinguistic group ancestral to modern Scandinavians, defined as speakers of Old Norse from about the 9th to the 13th centuries.
Norse may also refer to:

Final Answer: [ANSWER|The Norse originated from North Germanic countries, including Denmark, Norway, Sweden, and Iceland.]
```

**Key-Value Store** LMQL can also access the state of the surrounding python interpreter. To showcase this, we show how to use the `assign` and `get` functions to store and retrieve values in a simple key-value store.

```lmql
# implement a simple key value storage
# with two operations
storage = {}
def assign(key, value): 
    # store a value
    storage[key] = value; return f'{{{key}: "{value}"}}'
def get(key): 
    # retrieve a value
    return storage.get(key)

# instructive prompt, instructing the model to how use the storage
"""In your reasoning you can use actions. You do this as follows:
`action_name(<args>) # result: <inserted result>`
To remember things, you can use 'assign'/'get':
- To remember something:
`assign("Alice", "banana") # result: "banana"`
- To retrieve a stored value:
`get("Alice") # result: "banana"`
Always tail calls with " # result". Using these actions, let's solve
the following question.\n"""

# actual problem statement
"""
Q: Alice, Bob, and Claire are playing a game. At the start 
of the game, they are each holding a ball: Alice has a black 
ball, Bob has a brown ball, and Claire has a blue ball. 

As the game progresses, pairs of players trade balls. First, 
Bob and Claire swap balls. Then, Alice and Bob swap balls. 
Finally, Claire and Bob swap balls. At the end of the game, 
what ball does Alice have?
A: Let's think step by step.
"""

# core reasoning loop
for i in range(32):
    "[REASONING]" where STOPS_AT(REASONING, "# result") and \
                        STOPS_AT(REASONING, "Therefore, ")
    
    if REASONING.endswith("# result"):
        cmd = REASONING.rsplit("`",1)[-1]
        cmd = cmd[:-len("# result")]
        "{eval(cmd)}`\n"
    else:
        break

# generate final answer
"Therefore at the end of the game, Alice has the[OBJECT]" \
    where STOPS_AT(OBJECT, ".") and STOPS_AT(OBJECT, ",")
```

```promptdown
# Model Output
(...)
A: Let's think step by step

[REASONING()| At the start of the game:
`assign('Alice', 'black') # result] {Alice: 'black'}
[REASONING()| `assign('Bob', 'brown') # result] {Bob: 'brown'}
[REASONING()| `assign('Claire', 'blue') # result] {Claire: 'blue'}

[REASONING()| After Bob and Claire swap balls:
`assign('Bob', 'blue') # result] {Bob: 'blue'}
[REASONING()| `assign('Claire', 'brown') # result] {Claire: 'brown'}

[REASONING()| After Alice and Bob swap balls:
`assign('Alice', 'blue') # result] {Alice: 'blue'}
[REASONING()| `assign('Bob', 'black') # result] {Bob: 'black'}

[REASONING()| After Claire and Bob swap balls:
`assign('Claire', 'black') # result] {Claire: 'black'}
[REASONING()| `assign('Bob', 'brown') # result] {Bob: 'brown'}

[REASONING()| At the end of the game, Alice has a blue ball:
`get('Alice') # result] blue`
Therefore at the end of the game, Alice has the [OBJECT| blue ball.]
```

As shown in the example above, the `assign` and `get` functions can be used to store and retrieve values in a simple key-value store. The model is merely instructed to make use of these functions in its reasoning. The query then implements logic to intercept any function use and insert the result of the function call into the reasoning. This allows the model to incorporate the state of the key-value store into its reasoning.




