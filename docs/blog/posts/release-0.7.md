---
date: 2023-09-23 10:10:00
title: LMQL 0.7 brings Procedural Prompt Programming
---

# LMQL 0.7 brings Procedural Prompt Programming

<span class="date">September 23, 2023</span>

Today, we are releasing LMQL 0.7. This series is the biggest update since the original release, including many community contributions. Next to several new main-line features like nested queries, the Generations API and the Chat API, it also includes several *experimental preview features*, allowing you to experiment with new incoming functionality before it is fully released.

LMQL 0.7 has also moved to [semantic versioning](https://semver.org) with the direct predecessor being 0.0.6.6. This means that the next feature release will be 0.8, and the next bugfix release will be 0.7.1.

## Nested Queries for Procedural Prompt Programming

In 0.7, you can now use [Nested Queries](../../docs/language/nestedqueries.md) to call an LMQL query as a nested function in the context of another query. For this, LMQL implements procedural programming for prompting. To illustrate, consider the following example:

```lmql
# chain of thought prompting strategy
@lmql.query
def chain_of_thought():
    '''lmql
    "A: Let's think step by step.\n [REASONING]"
    "Therefore the answer is[ANSWER]" where STOPS_AT(ANSWER, ".")
    return ANSWER.strip()
    '''

# top-level query
"Q: It is August 12th, 2020. What date was it \
    100 days ago? [ANSWER: chain_of_thought]"

ANSWER # May 4th, 2020
```

We first define a simple LMQL function `chain_of_thought` to do *chain-of-thought prompting*. In our top-level query, we can then call this function to decode an answer using the `[ANSWER: chain_of_thought]` syntax. During execution, LMQL then inserts the instructions and constraints from `chain_of_thought` into the top-level query, generates a value for `ANSWER`, and then removes the instructions and constraints again, only returning the final result.

**Nested queries are Prompt Function Calls.** This design of nested queries is inspired by the idea of *function or procedure calls* in traditional programming. Removing intermediate instructions and constraints also has parallels to the idea of *stack unwinding*, a technique to implement function calls in low-level languages. 

LMQL transfers these ideas to prompting, inheriting the general benefits of procedural programming:

- **Encapsulation and Model Focus** Nested Queries encapsulate and hide the prompting logic used to generate `ANSWER`, which means our top-level query is much cleaner and more concise. Further, by hiding intermediate instructions from the model in the context of the top-level query, we can reduce noise in the overall prompt, allowing the model to focus on the currently relevant information only, and not get distracted by previous intermediate steps.

- **Nesting and Reuse** LMQL queries can be nested arbitrarily deep, allowing you to reuse and combine queries modularly. For example, you could define a query `get_year` to extract a year from the response text, and then use this query in `chain_of_thought` to extract the date from the question. By achieving modularity for sub-prompts, nested queries also allow you to reuse prompts across different query programs.

To learn more about nested queries, please refer to the [relevant chapter in the documentation](../../docs/language/nestedqueries.md).

## Generations API

LMQL 0.7 adds the *Generations API*, a lightweight high-level library for LMQL-based text generation and scoring. The API was designed to be easy to use and does not require users to write any LMQL themselves:

```python
# obtain a model instance
m: lmql.LLM = lmql.model("openai/gpt-3.5-turbo-instruct")
# simple generation
m.generate_sync("Hello", max_tokens=10)
# -> Hello, I am a 23 year old female.
```
<br/>

Functions such as [`LLM.generate`](../../docs/lib/generations.html#llm-generate) and [`LLM.score`](../../docs/lib/generations.html#llm-score) allow you to generate and score text using any LMQL-support inference backend. The Generations API is also seamlessly compatible with standard LMQL, allowing you to switch and combine the two as needed. 

For more information, please refer to the [documentation](../../docs/lib/generations.html).

## Chat 

LMQL 0.7 adds a new [Chat API](../../docs/lib/chat.md), allowing you to easily deploy chatbots with just a couple lines of LMQL.

<img style="max-width: 80vw; width: 400pt; display: block; margin: auto;" src="https://github.com/eth-sri/lmql/assets/17903049/3f24b964-b9b6-4c50-acaa-b38e54554506"/>

LMQL Chat comes with custom output writers, that allow you to easily stream chatbot input and output over a variety of channels, including WebSockets, HTTP, and SSE. A simple `lmql chat` CLI tool was also added, that allows you to instantly launch your LMQL queries as fully interactive chatbots. 

We also provide documentation resources on how to get started with chatbot development with LMQL, including chapters on Chatbot Serving, Internal Reasoning and Defending against Prompt Injection. For more information, please refer to the [documentation](../../docs/lib/chat.md).

## Backends

LMQL 0.7 ships with three new backends for inference and tokenization:

* LMQL 0.7 adds support for OpenAI's newly released `gpt-3.5-turbo-instruct` model. In contrast to other 3.5 series models, this variant supports the *Completions API*, which means that LMQL constraints are compatible with it.

* LMQL now supports hosting models on [replicate.com](https://replicate.com) infrastructure, allowing you to run LMQL models in the cloud. To learn more, please refer to the [documentation](../../docs/models/replicate.md). Thanks a lot to community member [@charles-dyfis-net](https://github.com/charles-dyfis-net) for contributing this!

* LMQL added `sentencepiece` as an additional tokenization backend, specifically for `llama.cpp` models. This means, `llama.cpp` models can now be used without requiring `transformers` for tokenization. Thanks a lot to community member [@khushChopra](https://github.com/khushChopra) for contributing this.


## Inference Certificates

To make LLM inference more transparent and re-producible, LMQL 0.7 also adds [*inference certificates*](../../docs/lib/inference-certificates.md). An inference certificate is a simple data structure that records essential information needed to reproduce an inference result. Certificates can be generated for any LLM call that happens in an LMQL context.

To produce an inference certificate, pass `certificate=True` or `certificate=<filename>` to your query or generate call:

```truncated
# call and save certificate
say_hello(certificate="my-certificate.json")
```

The resulting certificate file provides a way to document, trace and reproduce LLM inference results by recording the *exact (tokenized) prompts* and information on the *environment and generation parameters*.

This can be helpful to better understand what is happening during inference, to debug issues, and to reproduce results. It also offers a way to document LLM failures, to better guide the discussion around the concrete capabilities and limitations of LLMs.

## Decorators

[Variable Decorators](../../docs/language/decorators.md) offer a new and simple way to call custom Python functions as part of the core generation loop in LMQL:

```lmql
def screaming(value):
    """Decorator to convert a string to uppercase"""
    return value.upper()

"Say 'this is a test':[@screaming TEST]"
```
```promptdown
Say 'this is a test': [TEST| THIS IS A TEST]
```

Similar to Python decorators, LMQL decorators are functions that take a variable as input and can wrap and modify its value. 

In the example above, we use the `@screaming` decorator to convert the value of `TEST` to uppercase. Decorators can be used to implement a wide range of custom functionality, including string normalization, datatype conversion, and more. LMQL also provides decorators that allow to stream or pre-process data during generation. For more information, please refer to the [documentation](../../docs/language/decorators.md).


## Documentation Update

The website and many chapters of the LMQL documentation have also been updated and extended and now include more examples and explanations. We have updated the visual design to make it easier to read and navigate. 

The documentation now also includes a *work-in-progress* [Language Reference](/docs/language/reference.md), which aims to provide a more comprehensive and formal description of LMQL's syntax and semantics, all in one place.

## Preview Features

Apart from many new core features, LMQL 0.7 also ships with several *experimental preview features*, allowing you to test drive new functionality before it has fully stabilized and is released as main-line functionality.

These features are marked as *experimental* and are not yet fully supported. We are releasing them to gather feedback and to allow users to test them out early on. Note that these features are subject to change and may be removed/modified in future releases.

### LMQL Actions <span class="beta badge">Preview</span>

*LMQL Actions* is the first version of LMQL's function calling layer. It allows you to expose arbitrary Python functions to the LLM reasoning loop and lets the model call them during generation. Function demonstration and the calling protocol can be both handled automatically by the LMQL runtime, allowing for simple use like this:

```{lmql}
def wiki(q): ...
def calc(expr): ...

"Q: What is the population of the US and Germany combined?"
"A: [REASONING]" where inline_use(REASONING, [wiki, calc])
```

To learn more about LMQL Actions, please refer to the [separate preview announcement here](https://lmql.ai/actions).

### Regex Constraints <span class="beta badge">Preview</span>

LMQL now has support for regex constraints, allowing you to use regular expressions to constrain the output of a variable. For example, the following query will always generate a valid date of the form `DD/MM`:

```{lmql}
"It's the last day of June so today is [RESPONSE]" where REGEX(RESPONSE, r"[0-9]{2}/[0-9]{2}")
```

### Types / Datatype Constraints <span class="beta badge">Preview</span>

LMQL is moving towards fully typed LLM generation. On the way there, we have started to add support for *dataclass constraints*, allowing you to constrain the output of a variable to a specific structured output schema:

```lmql
import lmql
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    age: int
    job: str

"Alice is a 21 years old and works as an engineer at LMQL Inc in Zurich, Switzerland.\n"
"Structured: [PERSON_DATA]\n" where type(PERSON_DATA) is Person

PERSON_DATA
# Person(name='Alice', age=21, job='engineer')
```

To achieve this, LMQL leverages constrained generation to make sure the LLM always produces all information required to populate a valid `Person` object. The resulting `PERSON_DATA` object can then be directly used like a regular Python object. Types are still in an early stage and we are working on adding more features and functionality. 


## Other Changes

* The LMQL playground can now be used from the Windows `cmd.exe`. Thanks a lot to community member [@mosheduminer](https://github.com/mosheduminer).

* LMQL/LMTP model backends can now be accessed [as Langchain `LLM` objects](https://github.com/eth-sri/lmql/blob/main/src/lmql/models/lmtp/lmtp_langchain.py) to use them in your Langchain pipelines. Thanks to [@4onon](https://github.com/4onon) for contributing this. 

* LMQL can now be [installed as a NixOS package](https://github.com/eth-sri/lmql/tree/main/scripts/flake.d). Thanks to [@charles-dyfis-net](https://github.com/charles-dyfis-net) for contributing this.

## 🎬 And that's a wrap!

LMQL 0.7 is a big release and we are excited to see what you will build with it. As always, please let us know if you have any questions, suggestions or bug reports, on [GitHub](https://github.com/eth-sri/lmql), [Discord](https://discord.gg/7eJP4fcyNT), [Twitter](https://twitter.com/lmqllang) or via [hello@lmql.ai](mailto:hello@lmql.ai).