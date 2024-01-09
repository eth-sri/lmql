---
sidebar: false
aside: true
prev: false
order: 100000
outline: [2,3,4]
---

# Language Reference

<div class="subtitle">LMQL's core syntax and semantics.</div>

::: tip
This document is a **work-in-progress effort** to provide a more formal description of LMQL, mainly discussing the syntactic form and corresponding semantics. Please feel free to reach out to the core team if you have any questions or suggestions for improvement.
:::

## Origins and Motivation

LMQL is a programming language for *LLM programming*. The primary design objective for LMQL is to provide a simple, yet powerful interface to implement (multi-part) reasoning flows that interact with LLMs in complex and algorithmically controlled ways. 

At the core of LMQL, the following components are of particular importance to achieve this goal:

* Robust and type-safe generation via a **constrained decoding engine**.

* A lightweight **programming model for prompting**, including ways to abstract and modularize query code.

* A **vendor-agnostic** abstraction over optimized and parallelized **LLM inference**.

The overall goal is to provide a fast and reliable toolchain that facilitates LLM-powered reasoning and applications across domains. This includes already existing use-cases, such as simple chat applications and data parsing, but also extends to more complex applications such as autonomous agents, large-scale data processing, and programmatic reasoning and planning.

## Using LMQL

LMQL's [current reference implementation](#reference-implementation) is written in Python and can be used in a variety of ways:

* The `lmql playground` offers an interactive interface for running, debugging and experimenting with LMQL programs. It is the recommended way to get started with LMQL. An online version of the playground is available at [lmql.ai/playground](https://lmql.ai/playground).

* LMQL is available as a Python library, with the `lmql.query` function offering a simple way to use LMQL directly from within Python. For more information, please refer to general [Documentation](overview.md).

* The `lmql run` CLI tool can used to run LMQL programs directly from the command line.

For more information and example-based discussion on how to use LMQL, please refer to the [Getting Started](../index.md) guide.

## Syntax

The LMQL language comprises two syntax variants:

* The modern, more minimalistic [standard syntax](#standard-syntax) that relies on a very small set of language constructs in an otherwise standard Python environment. This syntax is the main focus for the continued development of LMQL.

* A *legacy* [standalone syntax](#standalone-syntax) that is more static in nature but relevant for standalone LMQL use-cases.

Both syntax variants are compatible and can be used interchangeably. 

::: details Grammar Notation

We rely on a slightly modified variant of [EBNF](https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_form) to describe the LMQL syntax. 

We denote non-terminals like `<SENTENCE>` and terminals like `"dog"`. The `[...]?` operator denotes an optional element, while the `*` operator denotes a repetition of zero or more elements. The `|` operator denotes a choice between two or more elements and non-quoted terminals are regular expressions to match against. 

To avoid notational overhead, we assume that Python fragments like `<python.Expr>`, refer to standard Python, with the adaptations that arising sub-derivations can also refer back to LMQL expressions (namely [<QUERY_STRING>](#query-strings) and [<CONSTRAINT_EXPR>](#constraints)), when appropriate.

```grammar
<SENTENCE> := "The quick" ["brown"]? <SUBJECT> <VERB> "over the lazy dog."
<SUBJECT> := "fox" | "dog"
<VERB> := "jumps" | "hops" | [.*]{4}
```

**Examples of valid `<SENTENCE>` derivations:**    
```lmql
"The quick fox jumps over the lazy dog."
"The quick brown fox jumps over the lazy dog."
"The quick dog jumps over the lazy dog."
"The quick brown dog hops over the lazy dog."
"The quick dog A9_D over the lazy dog."
```

:::

### Standard Syntax

LMQL's modern syntax can be read as standard Python code, with the addition of one new construct: [query strings](#query-strings). Query strings are just top-level string expressions, that are interpreted as prompts to the underlying LLM. The following grammar describes this syntax in detail.

```grammar
<LMQL_PROGRAM> := # (optional) decoder clause
                  [ [<DECODER>](decoder-clause) [ '(' [<python.KeywordArguments>](python-fragments) ')' ]? ]? 
                  # program body
                  <STMT>*

<STMT> := # regular python statements
                 [<python.Stmt>](python-fragments) |
                 # query strings
                 [<QUERY_STRING>](query-strings) |
                 # query strings with inline constraints
                 [<QUERY_STRING>](query-strings) 'where' [<CONSTRAINT_EXPR>](constraints) |
                 # query strings with distribution clause
                 [<QUERY_STRING>](query-strings) 'distribution' [<DISTRIBUTION_EXPR>](distribution-clauses)) |

[<QUERY_STRING>](query-strings) := [<...>](query-strings)

[<CONSTRAINT_EXPR>](constraints) := [<...>](constraints)

[<DISTRIBUTION_EXPR>](distribution-clauses) := <VARIABLE> 'in' [<python.Expr>](python-fragments)
```

::: info Examples of Valid Programs

Simple program with two [query strings](#query-strings)

```lmql
"Hello [WHO]"
"Goodbye [WHO]"
```

Python programs without LMQL constructs are also valid LMQL programs

```python
a = 12
print("Hello, world!")
print("Goodbye, world!", a)
```

LMQL programs with control flow

```lmql
"Q: What is 2x2? [ANSWER]"
while ANSWER != 4:
    "Incorrect, try again: [ANSWER]"
"Good job!"
```

Program with [query strings](#query-strings), [constraints](#constraints) and string interpolation

```lmql
a = "Alice"
"Hello {a} [WHO]" where len(TOKENS(WHO)) < 10
print(WHO)
```

Program with [query strings](#query-strings) and [distribution clauses](#distribution-clauses)

```lmql
"Greet Alice\n:"
"Hello [WHO]" distribution WHO in ["Alice", "Bob"]
```

:::

### Standalone Syntax

The standalone query syntax is less flexible than the modern syntax variant and generally considered legacy. It is still supported for standalone use-cases, but users are advised to rely on the modern syntax going forward. Nonetheless, it shares many syntactic constructs with the modern syntax, and is thus described in this document as well.

```grammar
<STANDALONE_QUERY> := [ [<DECODER>](decoder-clause) [ '(' [<python.KeywordArguments>](python-fragments) ')' ]? ]? 
                        <PROMPT>
                     [ 'from' [<MODEL_EXPR>](model-expressions) ]?
                     [ 'where' [<CONSTRAINT_EXPR>](constraints) ]?
                     [ 'distribution' [<DISTRIBUTION_EXPR>](distribution-expr) ]?

[<DECODER>](decoder-clause) := 'argmax' | 'sample' | 'beam' | 'beam_var' | 
             'var' | 'best_k' | [<python.Identifier>](python-fragments)

<PROMPT> := [<QUERY_STRING>](query-strings) | [<python.Stmt>](python-fragments)

[<QUERY_STRING>](query-strings) := [<...>](query-strings)

[<MODEL_EXPR>](model-expressions) := "lmql.model" "(" [<python.Arguments>](python-fragments) ")" |
                [<python.StringLiteral>](python-fragments)

[<CONSTRAINT_EXPR>](constraints) := [<...>](constraints)

[<DISTRIBUTION_EXPR>](distribution-clauses) := <VARIABLE> 'in' [<python.Expr>](python-fragments)

VARIABLE := [<python.Identifier>](python-fragments)
```

::: info Examples

decoder clause + from
```lmql
argmax "What is the capital of France? [ANSWER]" from "gpt2"
```

decoder clause + where
```
argmax "What is the capital of France? [ANSWER]" \
    where len(TOKENS(ANSWER)) < 10
```

decoder clause + distribution
```
argmax "What is the capital of France? [ANSWER]" \
    distribution ANSWER in ["A", "B"]
```

decoder clause + from + where + distribution
```
argmax 
    "What is the capital of France? [ANSWER]" 
from
    "gpt2"
distribution 
    ANSWER in ["A", "B"]
```

:::

### Decoder Clause

```grammar
DECODER_CLAUSE := [<DECODER>](decoder-clause) [ '(' [<python.KeywordArguments>](python-fragments) ')' ]?
```

The decoder clause defines the decoding algorithm to be used for generation. It is optional and defaults to `argmax`. 

**Algorithms** `<DECODER>` is one of the runtime-supported decoding algorithms, e.g. `argmax`, `sample`, `beam`, `beam_var`, `var`, `best_k`, or a custom decoder function. For a detailed description please see the [Decoding](../language/decoding.md) documentation chapter.

**Program-Level Decoding** Per query program, only one decoder clause can be specified, i.e. a single decoding algorithm is used to execute all query strings and placeholder variables. This is because decoders act on the program level, and branchingly explore several possible continuations of the program, based on the current program state.


### Query Strings

Query strings represent the core construct for prompt construction and model interaction. They read like top-level string expressions in Python, but are interpreted as prompts to the underlying LLM, including placeholder variables, constraints and string interpolation:

```grammar
QUERY_STRING := <CONSTRAINED_QSTRING> | <DISTRIBUTION_QSTRING> | <PURE_QSTRING>

# qstring with constraints, e.g. "Hello, [NAME]!" where len(TOKENS(NAME)) < 10
<CONSTRAINED_QSTRING> := <PURE_QSTRING> 'where' [<CONSTRAINT_EXPR>](constraints)

# qstring with distribution clause, e.g. "Hello, [NAME]!" distribution NAME in ["Alice", "Bob"]
<DISTRIBUTION_QSTRING> := <PURE_QSTRING> 'distribution' <VARIABLE> 'in' [<python.Expr>](python-fragments)

# qstring without constraints, e.g. "Hello, [NAME]!"
<PURE_QSTRING> := <python.StringDelimiter>
                  ( 
                      '.*' | # arbitrary string prompt
                      <PLACEHOLDER_VARIABLE> |
                      <STRING_INTERPOLATION> 
                  )* '"'
                  <python.StringDelimiter>

# placeholder variable, e.g. "[NAME]"
<PLACEHOLDER_VARIABLE> := "[" [<python.Identifier>](python-fragments) "]" |
                          # with type/tactic annotation
                          "[" [<python.Identifier>](python-fragments) ":" [<python.Expr>](python-fragments) "]" |
                          # with decorator
                          "[" <DECORATOR>?  [<python.Identifier>](python-fragments) "]" |
                          # with decorator and type/tactic
                          "[" <DECORATOR>?  [<python.Identifier>](python-fragments) ":" [<python.Expr>](python-fragments) "]"

# decorator, e.g. "@fct(a=12)"
<DECORATOR> := "@" [<python.Call>](python-fragments) | "@" [<python.Identifier>]

# standard Python f-string interpolation
<STRING_INTERPOLATION> := "{" <python.Expr> "}"
```

::: details Examples

Without variables:
```
"Hello, world!" 
```
With two variable:
```
"Hello, [NAME] and [NAME2]!"
```
With constraints:
```
"Hello, [NAME]!" where len(TOKENS(NAME)) < 10
```
With decorator:
```
"Hello, [@fct(a=12) NAME]!"
```
With type annotation:
```
"Your Age: [AGE:int]!"
```
With [nested call](../language/nestedqueries.md) (tactic annotation):
```
"Q: What is 2x2? A: [ANSWER: chain_of_thought(shots=2)]"
```
With string interpolation:
```
NAME = "Alice"
"Hello, {NAME}, how old are you: [AGE:int]?"
```

:::

::: warning Escaping

To avoid ambiguities, the following characters need to be escaped in query strings:

* `[` and `]` need to be escaped as `[[` and `]]`.
* `{` and `}` need to be escaped as <code>{ {</code> and `}}`.

Python string escaping rules also apply, e.g. string delimiters need to be escaped to disambiguate string boundaries (e.g. `"\""`).

:::

#### Prompt Construction

The current prompt used for LLM invocations throughout execution, is defined by the concatenation of all query strings executed so far, where placeholder variable are substituted by the respective generated values. Query strings are evaluated along the program's control flow (e.g. multiple times when called in loops), and left-to-right within a single query string with multiple placeholders. At any point during execution, when an LLM is invoked, the currently active prompt is what is passed to the model.

For this, newline characters `\n` must always be included explicitly, if desired.

::: details Example: Prompt Construction

As an example of prompt construction, consider the following program and its corresponding prompt state during execution:

<div style="display: flex; flex-direction: row; justify-content: space-between; align-items: center;">

<div style="width: 50%; margin: 3pt 20pt 0pt 0pt;">

```lmql
numbers::

"Hello, [NAME] and [NAME2]\n"
        ⬆ 1       ⬆ 2

"How are you doing?"
⬆ 3

" [FEELINGS]"
⬆ 4        ⬆ 5
```

</div>

<div>

| Point | Prompt | Active Variable | Action |
| ----- | ------ | --------------------- | ------ |
| `1`     | `"Hello, "` | `NAME` | Generate the value of `NAME` |
| `2`     | `"Hello, <generated NAME> and "` | `NAME2` | Generate the value of `NAME2` |
| `3`     | `"Hello, <generated NAME> and <generated NAME2>\n"` | - | Continue with program execution |
| `4`     | `"Hello, <generated NAME> and <generated NAME2>\nHow are you doing? "` | `FEELINGS` | Generate the value of `FEELINGS` |
| `5`     | `"Hello, <generated NAME> and <generated NAME2>\nHow are you doing? <generated FEELINGS>"` | - | End program execution |

</div>

</div>

:::

#### Placeholder Variables

Placeholder variables define the templated placeholders an LLM generates text for, and are denoted by `[...]` square brackets. With respect to the program state, placeholder variables assign the generated values to program variables of the same name.

::: details Example: Variable Assignments

With respect to variable assignment, the following code

```lmql
NAME = "Alice"
"Hello [NAME] and [NAME2]"
```

can be understood as the following pseudo-code:

```python
NAME = "Alice"
NAME, NAME1 = model.fill_placeholders("Hello [NAME] and [NAME2]")
```

The previous value of `NAME` is thus overwritten, after executing the query string.

:::

#### Query String Constraints and Distributions

Query strings can also be constrained using the `"..." where ...` syntax. This defines [decoding constraints](#constraints), that only apply locally during generation of the respective query string. For more information, see [constraints](#constraints).

Similarly, distributions can be constructed using the `"..." distribution VAR in [...]` syntax. This generates scores for given alternative values for the respective variable, and returns the resulting likelihoods. For more information, see [distribution clauses](#distribution-clauses)

::: details Example: Constrained Query String

A query string with a constraint on the variable `NAME`:

```lmql
"Hello, [NAME]!" where len(TOKENS(NAME)) < 10
"Another [NAME]"
```

The token length constraint on `NAME` only applies to generations that are invoked for the first query string, i.e. `"Hello, [NAME]!"`. The next query string `"Another [NAME]"` is not affected by the constraint.

:::
#### Types and Tactics

Next to the variable name, a tactic or type can be specified using the `"[VAR: <tactic>]"` syntax. Syntactically, a tactic expression can be an arbitrary Python expression, however, at runtime, the interpreter expects one of the following:

* A type reference like `int`, supported by the runtime as [LMQL type expression](#types)

* A regex expression like `r"[a-z]+"`, to be enforced as a regex constraint.

* A reference to another [LMQL query function](#query-functions) like `chain_of_thought(shots=2)`, to be executed as a [nested query](../language/nestedqueries.md).

::: details Example: Tactic Expressions

A query string with a integer type annotation on the variable `AGE`:

```lmql
"Your Age: [AGE:int]!"
```

A query string with regex tactic on the variable `NAME`:

```lmql
"Hello, [NAME:r"[a-z]+"]!"
```

A query string decoded using a [nested query](../language/nestedqueries.md) on the variable `ANSWER`:

```lmql
"Q: What is 2x2? A: [ANSWER: chain_of_thought(shots=2)]"
```

:::

#### String Interpolation 

Query strings are compiled to Python `f-strings` and thus implement regular Python string interpolation semantics using the `"Hello {...}"` syntax, e.g. `"Hello {NAME}"` evaluates to `"Hello Alice"`, given the current program state assigns `NAME = "Alice"`.

### Constraints

```grammar
[<CONSTRAINT_EXPR>](constraints) := [<CONSTRAINT>](constraints) 'and' CONSTRAINT_EXPR |
                     [<CONSTRAINT>](constraints) 'or' CONSTRAINT_EXPR |
                     'not' [<CONSTRAINT>](constraints) |
                     [<CONSTRAINT>](constraints)
```

::: danger
TODO
:::


### Model Expressions

```grammar
<MODEL_EXPR> := "lmql.model" "(" <python.Arguments> ")" |
                <python.StringLiteral>
```

::: danger
TODO
:::

### Distribution Clauses

```grammar
<DISTRIBUTION_EXPR> := <VARIABLE> 'in' [<python.Expr>](python-fragments)
```

::: danger
TODO
:::

### Python Fragments

LMQL relies on the following Python grammar fragments, to express parts of the LMQL language.

For reference, the [Python grammar is available here](https://docs.python.org/3/reference/grammar.html).

| Fragment | Description |
| -------- | ----------- |
| `<python.Identifier>` | A Python identifier, as defined as `NAME` in the Python grammar. Examples: `a`, `b`, `my_var1`, `MY_VAR2` |
| `<python.StringLiteral>` | A Python string literal, as defined as `STRING` in the Python grammar. This includes supports for string delimiters, such as single quotes (`'`), double quotes (`"`), and triple quotes (`'''` or `"""`). Examples: `'hello'`, `"world"`, `'''hello'''`, `"""world"""` |
| `<python.StringDelimiter>` | A Python string delimiter, e.g. `'`, `"`, `'''`, or `"""`. |
| `<python.Expr>` | A regular Python expression, as defined as `expression` in the Python grammar. Examples: `a`, `a+b`, `a(b=12)`, `a if b else c`, `a > 2`, `a == b` |
| `<python.Stmt>` | A regular Python statement, as defined as `simple_stmt` or `compound_stmt` in the Python grammar. This includes control flow statements, such as `if`, `for`, `while`, `try`, `with`, etc. |
| `<python.Call>` | A Python function call, as defined as `call` in the Python grammar. This includes expressions like `a()`, `a(b=12)`, `a(b=12, c=13)`, `a(b=12, c=13, **some_dict)`. |
| `<python.KeywordArguments>` | Function call keyword arguments, as defined as `kwargs` in the Python grammar. This includes expressions like  `()`, `(a=1, b=2)`, `(a=1, b=2, **some_dict)`. |
| `<python.Arguments>` | Function call arguments, as defined as `args` in the Python grammar. This includes expressions like  `()`, `(a, b)`, `(a, 1, 2, c=2)`, `(a, b, *some_iterable, **some_dict)`.

## Types 

<Badge text="Work in Progress"/>

LMQL types can be used to annotate variable during generation, to enforce type constraints on the generated values. The resulting value has two representations:

* A **prompt representation**: The value that is used in the prompt, e.g. `1234` would be represented as the string `"1234"`.

* A **program representation**, the value that is returned when the corresponding variable is accessed from the program, e.g. `1234` would be represented as the Python integer `1234`.

This distinction helps enable expressive prompting, i.e. represent values in a way that is suitable for the LLM, while also allowing for type-safe and convenient programmatic access to the generated values.


| Type | Description | Prompt Representation | Program Representation |
| ---- | ----------- | --------------------- | ---------------------- |
| `str` (default) | String type, e.g. `"hello"`, `"world"`, ... | `str_value` | [`class str`](https://docs.python.org/3/library/stdtypes.html#str) |
| `int` | Integer type, e.g. `1`, `2`, `3`, ... | `str(int_value)` | [`class int`](https://docs.python.org/3/library/functions.html#int) |

The default type of all placeholder variables is `str`. To change the type of a variable, the type can be specified as part of the placeholder variable declaration, e.g. `[NAME:int]` or `[NAME:float]`, as discussed in the [query strings](#types-and-tactics) section.

## Query Functions

Query functions are the functional building blocks for LMQL programs.

LMQL query functions are defined similar to regular Python function syntax, but using the `@lmql.query` decorator and by providing the LMQL code as part of the docstring, *not* the function body.

```lmql
@lmql.query
def my_query_function(person):
    '''lmql
    "Greet {person}. Hello [NAME]!"
    '''
```

From within Python, the same syntax can used to construct Python-callable query functions. Please see to the documentation chapter on [Python Integration](../lib/python.md) for more information.

LMQL query function can also be declared as [`async`](https://docs.python.org/3/library/asyncio-task.html#coroutine) functions, which enables asynchronous execution.

### Function Calling and Arguments

A query function can be called as a standard function from within LMQL or Python code. It can also be called as a [nested query](../language/nestedqueries.md) from within a query string. `async` query functions require the `await` keyword to be used.

**Arguments** In addition to the function arguments specified in the function signature, query functions also provide the following additional arguments, that can be used to control the generation process:

* `model`: The [`lmql.LLM`](../lib/generations.md#lmql-llm-objects) model reference (or string identifier) to be used for generation.
* `decoder`: The decoding algorithm to be used for generation. See also the [decoder clause](#decoder-clause) section.
* `output_writer`: The output writer callback to be used during generation. See also documentation chapter on [output streaming](../lib/output.html) section.
* `**kwargs`: Additional keyword arguments, passed to decoder and interpreter, such as `temperature`, `chunksize`, etc.

## Reference Implementation

LMQL's current reference implementation is written in Python and also available as a Python library. The reference implementation of the syntax and semantics described in this document is available via Git at [github.com/eth-sri/lmql](https://github.com/eth-sri/lmql).

### Compiler and Runtime

The LMQL Python compiler translates LMQL programs into asynchroneous, brancheable Python code according to the semantics described in this document. The resulting program is then executed using the LMQL runtime, which implements (constrained) decoding algorithms, optimizations and model support via several backends.

### Hybrid Parser

For parsing, the implementation leverages a hybrid approach, largely relying on the existing Python parser (`ast.parse`) and grammar, adding additional parsing logic only for LMQL-specific constructs. This approach allows us to be compliant with the Python grammar, while also allowing us to extend the language with additional constructs, that are not part of the original Python grammar. To parse the standalone syntax, we segment the input on a token level and then call the parser several times to obtain the final AST for e.g. the prompt clause, the where clause or the distribution clause.

<style>
h4 {
    margin-top: 50pt;
}
</style>