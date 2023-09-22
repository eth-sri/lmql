# Generations API

The *Generations API* is a small library with the goal of providing high-level access to LMQL core features, such as inference backends, constrained generation, and advanced caching and scoring. The Generations API is designed to be easy to use, and does not require users to write any LMQL themselves.

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

- **`lmql.LLM`** At the core of the Generations API are `lmql.LLM` objects. Using the `lmql.model(...)` constructor, you can access a wide range of different models, as described in the [Models](../language/models.rst) chapter. This includes support for models running in the same process, in a separate worker process or API-based models.

- [**`lmql.LLM.generate(...)`**](#lmql-generate) is a simple function to generating text completions based on a given prompt. This can be helpful to quickly obtain single-step completions, or to generate a list of completions for a given prompt.

- [**`lmql.LLM.score(...)`**](#lmql-score) allows you to directly access the scores, your model assigns to the tokenized representation of your input prompt and continuations. This can be helpful for tasks such as classification or ranking.


**Compatibility** For more advanced use cases, the Generation API seamlessly blends with standard LMQL, allowing users to gradually adopt the full language runtime over time, if their use cases require it.

**Implementation** Internally, the Generations API is implemented as a thin wrapper around LMQL, and thus benefits from all the features of LMQL, such as caching, parallelization, and more. The API is fully asynchronous, and can be used with any async framework, such as `asyncio`, `trio`, or `curio`. Alternatively, the API can also be used synchronously, using the `*_sync` variants of the API functions.

## API Reference

The Generation API is available directly in the top-level namespace of the `lmql` module:

### `lmql.generate(...)`

```python
async def lmql.generate(
    prompt: str, 
    max_tokens: Optional[int] = None, 
    model: Optional[Union[LLM, str]] = None, 
    **kwargs
) -> Union[str, List[str]]
```

`lmql.generate` generates text based on a given prompt, using a given model as the generation backend. 

**Arguments**

- `prompt`: The prompt to generate from.
- `max_tokens`: The maximum number of tokens to generate. If `None`, text is generated until the model returns an *end-of-sequence* token.
- `model`: The model to use for generation. If `None`, the default model is used.
- `**kwargs`: Additional keyword arguments are passed to the underlying LMQL query program. This can be used to specify the `decoder`, options like `chunksize` or `n`, or any other model or decoder arguments.

**Return Value** The function returns a string or a list of strings, depending on the decoder in use (`argmax` yields a single sequence, `decoder="sample", n=2` yields two sequences, etc.).


### `lmql.generate_sync(...)`

Synchronous version of `lmql.generate`.

### `lmql.score`

```python
async def score(
    prompt: str,
    values: Union[str, List[str]],
    model: Optional[Union[str, LLM]] = None, 
    **kwargs
) -> lmql.ScoringResult
```

`lmql.score` scores different continuation `values` for a given `prompt`.

**Arguments**

- `prompt`: The prompt to score from.
- `values`: The values to score.
- `model`: The model to use for scoring. If `None`, the default model is used.

**Return Value** The function returns an `lmql.ScoringResult` object, which contains the scores for each value, as well as the prompt and values used for scoring.

### `lmql.score_sync(...)`

Synchronous version of `lmql.score`.

### `lmql.set_default_model(...)`

```python
def set_default_model(model: Union[str, LLM])
```

Sets the model instance to be used when no 'from' clause or @lmql.query(model=<model>) are specified.

This applies globally in the current process.


### `lmql.LLM` Objects 

`lmql.LLM` objects represent a specific model, and provide methods for generation and scoring. An `lmql.LLM` is instantiated using `lmql.model(...)` and can be passed as-is to LMQL query programs (in the `from` clause) or to the `lmql.generate` and `lmql.score` functions.

```python
def get_tokenizer(self) -> LMQLTokenizer
```

**Return Value** Returns the tokenizer used by the model.

```python
async def generate(
    self,
    prompt: str, 
    max_tokens: Optional[int] = None, 
    **kwargs
) -> Union[str, List[str]]
```

Model-bound version of [`lmql.generate`](#lmql-generate).

```python
def generate_sync(self, *args, **kwargs):
```

Synchronous version of `lmql.LLM.generate`.

```python
async def score(
    self,
    prompt: str,
    values: Union[str, List[str]],
    **kwargs
) -> lmql.ScoringResult
```

Model-bound version of [`lmql.score`](#lmql-score).

```python
def score_sync(self, *args, **kwargs)
```

Synchronous version of `lmql.LLM.score`.
