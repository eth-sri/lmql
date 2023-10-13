---
outline: [2,3]
---

# Generations API <span class="badge">NEW</span>

<div class="subtitle">A simple Python API for LMQL-based text generation and scoring.</div>

The *Generations API* is a lightweight library with the goal of providing high-level access to LMQL features, such as its inference backends, (constrained) generation, and scoring. The API was designed to be easy to use and does not require users to write any LMQL themselves.

<div style="margin-bottom: -10pt"></div>

## Overview

To illustrate the Generations API, let's look at a simple example of generating and scoring text using the `openai/gpt-3.5-turbo-instruct` model:

```
import lmql

# obtain a model instance
m: lmql.LLM = lmql.model("openai/gpt-3.5-turbo-instruct")

# simple generation
m.generate_sync("Hello", max_tokens=10)
# -> Hello, I am a 23 year old female.

# sequence scoring
m.score_sync("Hello", ["World", "Apples", "Oranges"])
# lmql.ScoringResult(model='openai/gpt-3.5-turbo-instruct')
# -World: -3.9417848587036133
# -Apples: -15.26676321029663
# -Oranges: -16.22640037536621
```

The snippet above demonstrates the different components of the Generations API:

- **`lmql.LLM`** At the core of the Generations API are `lmql.LLM` objects. Using the `lmql.model(...)` constructor, you can access a wide range of different models, as described in the [Models](../models/index.md) chapter. This includes support for models running in the same process, in a separate worker process or cloud-based models available via a API endpoint.

- [**`lmql.LLM.generate(...)`**](#lmql-generate) is a simple function to generating text completions based on a given prompt. This can be helpful to quickly obtain single-step completions, or to generate a list of completions for a given prompt.

-   [**`lmql.LLM.score(...)`**](#lmql-score) allows you to directly access the scores, your model assigns to the tokenized representation of your input prompt and continuations. This can be helpful for tasks such as classification or ranking. 
    
    The result is an [`lmql.ScoringResult`](https://github.com/eth-sri/lmql/blob/main/src/lmql/api/scoring.py) object, which contains the scores for each continuation, as well as the prompt and continuations used for scoring. It provides a convenient interface for score aggregation, normalization and maximum selection.


**Compatibility** For more advanced use cases, the Generation API seamlessly blends with standard LMQL, allowing users to gradually adopt the full language runtime over time, if their use cases require it.

**Implementation** Internally, the Generations API is implemented as a thin wrapper around LMQL, and thus benefits from all the features of LMQL, such as caching, parallelization, and more. The API is fully asynchronous, and should be used with `asyncio`. Alternatively, all API funcationality is also available synchronously, using the `*_sync` variants of the functions.

## `lmql.LLM` Objects

At the core, `lmql.LLM` objects represent a specific language model and provide methods for generation and scoring. An `lmql.LLM` is instantiated using [`lmql.model(...)`](../models/index.md) and can be passed [as-is to LMQL query programs](../models/index.md#loading-models) or to the top-level [`lmql.generate`](#lmql-generate) and [`lmql.score`](#lmql-score) functions.

### `LLM.generate(...)`

```python
async def generate(
    self,
    prompt: str, 
    max_tokens: Optional[int] = None, 
    decoder: str,
    **kwargs
) -> Union[str, List[str]]
```

Generates a text completion based on a given prompt. Returns the full prompt + completion as one string.

**Arguments**

- `prompt: str`: The prompt to generate from.
- `max_tokens: Optional[int]`: The maximum number of tokens to generate. If `None`, text is generated until the model returns an *end-of-sequence* token.
- `decoder: str`: The [decoding algorithm](../language/decoding.md) to use for generation. Defaults to `"argmax"`.
- `**kwargs`: Additional keyword arguments that are passed to the underlying LMQL query program. These can be useful to specify options like `chunksize`, decoder arguments like `n`, or any other model or decoder-specific arguments.

**Return Value** The function returns a string or a list of strings, depending on the decoder in use (`decoder=argmax` yields a single sequence, `decoder="sample", n=2` yields two sequences, etc.).

**Asynchronous** The function is asynchronous and should be used with [`asyncio`](https://docs.python.org/3/library/asyncio.html) and with `await`. When run in parallel, multiple generations will be batched and parallelized across multiple calls to the same model. For synchronous use, you can rely on [`LLM.generate_sync`](#llm-generate_sync), note however, that in this case, the function will block the current thread until generation is complete.

### `LLM.generate_sync(...)`

```python
def generate_sync(self, *args, **kwargs):
```

Synchronous version of [`lmql.LLM.generate`](#llm-generate).

### `LLM.score(...)`

```python
async def score(
    self,
    prompt: str,
    values: Union[str, List[str]]
) -> lmql.ScoringResult
```

Scores different continuation `values` for a given `prompt`.

For instance `await m.score("Hello", ["World", "Apples", "Oranges"])` would score the continuations `"Hello World"`, `"Hello Apples"` and `"Hello Oranges"`.

**Arguments**

- `prompt`: The prompt to use as a common prefix for all continuations.
- `values`: The continuation values to score. This can be a single string or a list of strings.

**Return Value** The result is an [`lmql.ScoringResult`](https://github.com/eth-sri/lmql/blob/main/src/lmql/api/scoring.py) object, which contains the scores for each continuation, as well as the prompt and continuations used for scoring. It provides a convenient interface for score aggregation, normalization and maximum selection.

**Asynchronous** The function is asynchronous and should be used with [`asyncio`](https://docs.python.org/3/library/asyncio.html) and with `await`. When run in parallel, multiple generations will be batched and parallelized across multiple calls to the same model. For synchronous use, you can rely on [`LLM.score_sync`](#llm-score-sync).

### `LLM.score_sync(...)`

```python
def score_sync(self, *args, **kwargs)
```

Synchronous version of [`lmql.LLM.score`](#llm-score).

## Top-Level Functions

The Generation API is also available directly in the top-level namespace of the `lmql` module. This allows for direct generation and scoring, 
without the need to instantiate an `lmql.LLM` object first.

### `lmql.generate(...)`

```python
async def lmql.generate(
    prompt: str, 
    max_tokens: Optional[int] = None, 
    model: Optional[Union[LLM, str]] = None, 
    **kwargs
) -> Union[str, List[str]]
```

`lmql.generate` generates text completions based on a given prompt and behaves just like [`LLM.generate`](#llm-generate), 
with the provided `model` instance or model name.

If no `model` is provided, the default model is used. See [`lmql.set_default_model`](#lmql-set_default_model) for more information.

### `lmql.generate_sync(...)`

Synchronous version of [`lmql.generate`](#lmql-generate).

### `lmql.score(...)`

```python
async def score(
    prompt: str,
    values: Union[str, List[str]],
    model: Optional[Union[str, LLM]] = None, 
    **kwargs
) -> lmql.ScoringResult
```

`lmql.score` scores different continuation `values` for a given `prompt` and behaves just like [`LLM.score`](#llm-score),
with the provided `model` instance or model name.

If no `model` is provided, the default model is used. See [`lmql.set_default_model`](#lmql-set_default_model) for more information.

### `lmql.score_sync(...)`

Synchronous version of [`lmql.score`](#lmql-score).

### `lmql.set_default_model(...)`

```python
def set_default_model(model: Union[str, LLM])
```

Sets the model to be used when no `from` clause or `@lmql.query(model=<model>)` are specified in LMQL. The default model applies globally in the current process and affects both LMQL queries and Generation API methods like [`lmql.generate`](#lmql-generate) and [`lmql.score`](#lmql-score) functions.

You can also specify the environment variable `LMQL_DEFAULT_MODEL` to set the default model.
