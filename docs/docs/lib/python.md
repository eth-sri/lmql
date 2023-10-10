---
outline: [2,3]
---

# Python Integration

<div class="subtitle">Use LMQL from Python.</div>

The primary way to use LMQL from your existing application is the `lmql` Python package. 

The `lmql` package offers a number of functions that allow you to define and run LMQL programs, directly from within Python.

## Query Functions

In Python, a piece of LMQL code is represented as a standard Python function. This means, you can define, parameterize and call LMQL code, directly from within your existing Python application. 

To enable this, LMQL offers three entry points:

* An `@lmql.query` decorator, to define LMQL query functions using standard `def` syntax, including support for capturing and accessing the surrounding Python scope.

* An `lmql.run` function, to directly run a string of LMQL code as a query, without having to define a function first.


* `lmql.F(...)` to evaluate pieces of LMQL code as pure lambda expressions, very similar to Python's `lambda` keyword.

All three methods internally construct an LMQL query function for the provided code. This chapter first discusses, how to define and run query functions using `lmql.query`, `lmql.run` and `lmql.F`, and then provides information on the [query result format](#query-results) and how to [configure queries](#query-configuration), e.g. to specify model, decoder and other parameters.

### `lmql.query`

The `@lmql.query` decorator allows you to directly expose a piece of LMQL code as a Python function, and call it from your existing code:

```lmql
@lmql.query
def chain_of_thought(question):
    '''lmql
    # Q&A prompt template
    "Q: {question}\n"
    "A: Let's think step by step.\n"
    "[REASONING]"
    "Thus, the answer is:[ANSWER]."

    # return just the ANSWER to the caller
    return ANSWER
    '''

print(chain_of_thought('Today is the 12th of June, what day was it 1 week ago?'))
```
```output
5th of June.
```
Note that the actual LMQL program is defined in the docstring of the function, allowing LMQL code to embed seamlessly.

Function arguments can be passed freely into the LMQL, and the return value of the function is passed back to the caller.

Variables from the surrounding context can also be captured by the query program, enabling access to the full power of Python from within LMQL.


::: info Jupyter Notebooks
You may encounter problems with the `@lmql.query` decorator in a Jupyter Notebook, because notebook environments are asynchronous, by default. To work around this, you can declare your query functions as `async` and use the `await` keyword when calling them.

Alternatively, you can install the [`nest_asyncio`](https://pypi.org/project/nest-asyncio/) package and call `nest_asyncio.apply()`, to enable nested event loops in your notebook.
:::

#### Variable Capturing

The `@lmql.query` decorator also allows you to access variables from the surrounding context, and make them available to the query program. This is done automatically by capturing the function's closure at definition time:

```lmql
import re

a = 12

@lmql.query
def query():
    '''lmql
    # access 'a' from the global namespace
    "Tell me a fun fact about {a}: [FACT]"
    # use imported 're' module
    return re.sub(r'\d+', '[NUMBER]', FACT)
    '''

print(query())
```
```output
[NUMBER] is the smallest number with exactly six divisors ([NUMBER], [NUMBER], [NUMBER], [NUMBER], [NUMBER], [NUMBER]).
```
As shown, within an `@lmql.query` function we have full access to the surrounding context, including any variables and imports defined in the outer scope. This allows for flexible integration of LMQL into your existing codebase.

### `lmql.run`

To run a string of LMQL code directly, without having to define a function first, you can use the `lmql.run` function:

```lmql

query_string = """
    "Q: {question}\\n"
    "A: Let's think step by step.\\n"
    "[ANSWER]"
"""

await lmql.run(query_string, question="What is 2x3?")
```
Note that with `lmql.run`, newline characters `\n` has to be a escaped as `\\n` in the query string, to avoid syntax errors.

To run synchronously, without `await`, you can use the `lmql.run_sync` function instead.


::: tip Escaping LMQL-specific Control Characters

When constructing queries from strings directly, always make sure to [escape LMQL-specific control characters correctly](../language/scripted-prompting.md#escaping), to avoid syntax errors in the resulting query program.

:::

#### Precompiling Queries

When using `lmql.run`, the query string will be compiled into a query function on every call. To avoid this, you can use the `lmql.query` function with a string, to create a function that will be compiled only once and can then be called multiple times:

```lmql
chain_of_thought = lmql.query("""
    "Q: {question}\\n"
    "A: Let's think step by step.\\n"
    "[ANSWER]"
""", is_async=False)

chain_of_thought("What is 2x3?")
```
Here, setting `is_async=False` ensures that the query can be executed synchronously.


### `lmql.F`

Lastly, `lmql.F` offers a lightweight way to evaluate pieces of LMQL code as simple lambda expressions, very similar to Python's `lambda` keyword. 

This offers a lightweight entryway to get started with integrating small LLM-based utilities in your code, without having to write a full LMQL program:

```lmql
summarize = lmql.F("Summarize the following in a \
                   few words: {data}: [SUMMARY]")

main_subject = lmql.F("What is the main subject (noun) \
                       of the following text? {data}: [SUBJECT]", 
                      "len(TOKENS(SUBJECT)) < 20")

text = "LMQL generalizes natural language prompting, ..."

summarize(data=text) # LMQL improves natural language prompting with 
# Python and fixed answer templates for better control over LLMs.

main_subject(data=text) # LMQL

```
Syntactically, an `lmql.F` expressions corresponds to a single [LMQL prompt statement](../language/scripted-prompting.md), without the `"` quotes. The `lmql.F` function returns a callable object, which can be used like a regular query function.

**Return Value** If the `lmql.F` contains only one placeholder variable, its generated value will be used as the return value of the function. Otherwise, a dictionary of all placeholder values will be returned.

**Constraints** To specify constraints in an `lmql.F` expression, you can pass a `constraints=...` string argument, which will be parsed and enforced like a `where` clause in a regular LMQL prompt statement.


## Query Results

In general, the result of query function is determined the use of `return` statements and the decoding algorithm used to execute the query:

### Query Functions With `return` statements

Query functions with `return` statements will return the value of the `return` statement. If a decoding algorithm with multiple output sequences is used (e.g. `sample(n=2)`), the return value will be a list of all `return` values.

```lmql
number = lmql.F("A random number: [JOKE: int]")

# sample two results
number(decoder="sample", n=2)
```
```result
[1, 25]
```
### Query Functions Without `return` statements

If no `return` statement is specified, the return value of the query function is a designated `lmql.LMQLResult` object, which contains the last assigned value of all variables defined in the query program:

```python
class LMQLResult:
    # full prompt with all variables substituted
    prompt: str
    # a dictionary of all assigned template variable values
    variables: Dict[str, str]
```

This allows to inspect the full query prompt, as well as individual variable values, after query execution:

```lmql
joke = lmql.query("""
    "Q: Tell me a joke about plants\\n"
    "A: [JOKE]"               
""", is_async=False)

joke()
```
```result
LMQLResult(prompt='Q: Tell me a joke about plants\nA: Why did the tomato turn red?\n\nBecause it saw the salad dressing!', variables={'JOKE': 'Why did the tomato turn red?\n\nBecause it saw the salad dressing!'}, distribution_variable=None, distribution_values=None)
```
If a decoding algorithm with multiple output sequences is used (e.g. `sample(n=2)`), the return value will be a list of all such `LMQLResult` objects.

## Query Configuration

To further control query execution (e.g. set the model, decoder, etc.), you can provide additional configuration parameters to any `lmql.query`, `lmql.run` or `lmql.F` call:

```python
@lmql.query(model=lmql.model("chatgpt"), decoder="argmax")
def chain_of_thought(question):
    ...
```

For this, the following arguments are supported:

* `model=<MODEL>` - The model to use for the query. This overrides the model specified in the query program. You can pass a model identifier or an [`lmql.model`](../../docs/models/index.md#loading-models) object.
* `decoder=<DECODER>` - The decoder to use for the query. This overrides any decoder specified by the query program. You can pass a any supported [decoder identifier](../../docs/language/decoding.md).
* `output_writer=<OUTPUT_WRITER>` - The output writer to use for streaming query progress during execution, see [Output Streaming](./output.md) for details. Defaults to `None`.
* `verbose=<True|False>` - Whether to print verbose logging output during query execution (API requests, LLM inference parameters, etc.). Defaults to `False`.
* `certificate=<True|False>` - Whether to produce an [inference certificate](../../docs/lib/inference-certificates.md) for the execution of a query. Defaults to `False`.

* `**kwargs` - Any extra keyword arguments are passed to the [decoding algorithm](../../docs/language/decoding.md). See [other decoding parameters](../../docs/language/decoding.md#other-decoding-parameters) for more details on the available parameters.

**Overriding Defaults** To override these configuration parameters at call time, you can also pass them as additional keyword arguments to the query function call:

```python
# executes 'chain_of_thought' with the 'gpt2-xl' model
chain_of_thought("What is the meaning of life?", 
                 model="gpt2-xl", temperature=0.5)
```

The result object is a dataclass with the following fields:

```python
class LMQLResult:
    # full prompt with all variables substituted
    prompt: str
    # a dictionary of all assigned template variable values
    variables: Dict[str, str]
```

