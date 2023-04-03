# Queries That Call Functions 

LMQL extends Python and can thus queries can incorporate arbitrary Python code including function calls.
In the simple example below we ask the model for a simple math problem and then use pythons `eval` function to evaluate the solution.

```{lmql}
name::simple_math

argmax
    "A simple math problem for addition (without solution, without words): [MATH]"
    "{eval(MATH[:-1])}"
from 
    'openai/text-davinci-003'
where
    STOPS_AT(MATH, "=")
```

```model-output
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

argmax
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
```







