# External Functions and Tools

LMQL extends Python and thus query code can incorporate arbitrary Python constructs including function calls.
For instance, below, we ask the model for a simple math problem and then use Python's `eval` function to evaluate the solution.

```{lmql}
name::simple_math

argmax
    "A simple math problem for addition (without solution, without words): [MATH]"
    "{eval(MATH[:-1])}"
from 
    'openai/text-davinci-003'
where
    STOPS_AT(MATH, "=")

model-output::
A simple math problem for addition (without solution, without words):
[MATH 7 + 8 =] 15
```



Here, similar to a python [f-string](https://peps.python.org/pep-0498), we use the `{}` syntax to insert the result of the `eval` function into the prompt. The `[:-1]` indexing is used to strip of the trailing `=` sign.

**Note:** While `eval` is handy for the examples in this section and allows to perform simple math, generally it can pose a security risk and should not be used in production.

## Calculator
Building on the previous example, we can now create a more complex calculator that can handle more complex expressions.
Here we define a function `calc` that leverages the build-in `re` library for Regular Expressions to strip the input of any non-numeric characters, before calling `eval`. Subsequently we can use `calc` to augment the reasoning capabilities of the large language model with a simple calculator.

Further, there we also call a function `gsm8k_samples` defined in a file `demo` within the LMQL library that returns a few-shot sample of the `gsm8k` dataset with examples of how to use the calculator.

```{lmql}
name::calculator
import re
from lmql.demo import gsm8k_samples

def calc(expr):
      expr = re.sub(r"[^0-9+\-*/().]", "", expr)
      return eval(expr)

argmax(openai_chunksize=128, max_len=2048)
      QUESTION = "Josh decides to try flipping a house.  He buys a house for $80,000 and then puts in $50,000 in repairs.  This increased the value of the house by 150%.  How much profit did he make?"
      # few shot samples
      "{gsm8k_samples()}"
      # prompt template
      "Q: {QUESTION}\n"
      "Let's think step by step.\n"
      for i in range(4):
         "[REASON_OR_CALC]"
         if REASON_OR_CALC.endswith("<<"):
            " [EXPR]"
            " {calc(EXPR)}>>"
         elif REASON_OR_CALC.endswith("So the answer"):
            break
      "is[RESULT]"
from 
      'openai/text-davinci-003'
where
      STOPS_AT(REASON_OR_CALC, "<<") and
      STOPS_AT(EXPR, "=") and
      STOPS_AT(REASON_OR_CALC, "So the answer")

model-output::
Q: Josh decides to try flipping a house.  He buys a house for $80,000 and then puts in $50,000 in repairs.  This increased the value of the house by 150%.  How much profit did he make?
Let's think step by step.
[REASON_OR_CALC Josh bought the house for $80,000 and put in $50,000 in repairs.
The value of the house increased by 150%, so the new value of the house is $80,000 + 150% of $80,000 = <<] [EXPR 80,000 + (80,000*1.5) =] 200000.0>> [REASON_OR_CALC $200,000.
The profit Josh made is the difference between the new value of the house and the amount he spent on it, which is $200,000 - $80,000 - $50,000 = <<] [EXPR 200,000 - 80,000 - 50,000 =] 70000>> [REASON_OR CALC $70,000.
So the answer] is [RESULT $70,000.]
```

## Beyond Calculators
Function use is not limited to calculators. In the example bellow we show how text retrieval, using Pythons `async`/`await` [syntax](https://docs.python.org/3/library/asyncio.html), can be used to augment the reasoning capabilities of the large language model. 

```{lmql}
name::wikipedia
async def wikipedia(q):
   from lmql.http import fetch
   try:
      q = q.strip("\n '.")
      pages = await fetch(f"https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro&explaintext&redirects=1&titles={q}&origin=*", "query.pages")
      return list(pages.values())[0]["extract"][:280]
   except:
      return "No results"

argmax
   "Q: From which countries did the Norse originate?\n"
   "Action: Let's search Wikipedia for the term '[TERM]\n"
   result = await wikipedia(TERM)
   "Result: {result}\n"
   "Final Answer:[ANSWER]"
from 
   "openai/text-davinci-003"
where
   STOPS_AT(TERM, "'")

model-output::
Q: From which countries did the Norse originate?
Action: Let's search Wikipedia for the term '[TERM Norse'].
Result: Norse is a demonym for Norsemen, a Medieval North Germanic ethnolinguistic group ancestral to modern Scandinavians, defined as speakers of Old Norse from about the 9th to the 13th centuries.
Norse may also refer to:

Final Answer: [ANSWER The Norse originated from North Germanic countries, including Denmark, Norway, Sweden, and Iceland.]
```

LMQL can also access the state of the surrounding python interpreter. To showcase this, we show how to use the `assign` and `get` functions to store and retrieve values in a simple key-value store.

```{lmql}
name::kvstore
# simple kv storage
storage = {}
def assign(key, value): storage[key] = value; return f'{{{key}: "{value}"}}'
def get(key): return storage.get(key)

argmax(n=1, openai_chunksize=128, max_len=2048, step_budget=4*2048)
   """In your reasoning you can use actions. You do this as follows:
   `action_name(<args>) # result: <inserted result>`
   To remember things, you can use 'assign'/'get':
   - To remember something:
   `assign("Alice", "banana") # result: "banana"`
   - To retrieve a stored value:
   `get("Alice") # result: "banana"`
   Always tail calls with " # result". Using these actions, let's solve the following question.
   
   Q: Alice, Bob, and Claire are playing a game. At the start of the game, they are each holding a ball: Alice has a black ball, Bob has a brown ball, and Claire has a blue ball. \n\nAs the game progresses, pairs of players trade balls. First, Bob and Claire swap balls. Then, Alice and Bob swap balls. Finally, Claire and Bob swap balls. At the end of the game, what ball does Alice have?
   A: Let's think step by step.\n"""
   for i in range(32):
      "[REASONING]"
      if REASONING.endswith("# result"):
         cmd = REASONING.rsplit("`",1)[-1]
         cmd = cmd[:-len("# result")]
         "{eval(cmd)}`\n"
      else:
         break
   """Therefore at the end of the game, Alice has the[OBJECT]"""
   assert "blue ball." in OBJECT
from 
   "openai/text-davinci-003"
where
   STOPS_AT(REASONING, "# result") and STOPS_AT(REASONING, "Therefore, ") and
   STOPS_AT(OBJECT, ".") and STOPS_AT(OBJECT, ",")            

model-output::
(...)
A: Let's think step by step

[REASONING At the start of the game:
`assign("Alice", "black") # result] {Alice: "black"}`
[REASONING `assign("Bob", "brown") # result] {Bob: "brown"}`
[REASONING `assign("Claire", "blue") # result] {Claire: "blue"}`

[REASONING After Bob and Claire swap balls:
`assign("Bob", "blue") # result] {Bob: "blue"}`
[REASONING `assign("Claire", "brown") # result] {Claire: "brown"}`

[REASONING After Alice and Bob swap balls:
`assign("Alice", "blue") # result] {Alice: "blue"}`
[REASONING `assign("Bob", "black") # result] {Bob: "black"}`

[REASONING After Claire and Bob swap balls:
`assign("Claire", "black") # result] {Claire: "black"}`
[REASONING `assign("Bob", "brown") # result] {Bob: "brown"}`

[REASONING At the end of the game, Alice has a blue ball:
`get("Alice") # result] blue`
Therefore at the end of the game, Alice has the [OBJECT blue ball.]
```

As shown in the example above, the `assign` and `get` functions can be used to store and retrieve values in a simple key-value store. The model is merely instructed to make use of these functions in its reasoning. The query then implements logic to intercept any function use and insert the result of the function call into the reasoning. This allows the model to incorporate the state of the key-value store into its reasoning.




