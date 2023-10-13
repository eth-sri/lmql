---
order: 0
---
# Overview

LMQL is a high-level, front-end language for text generation. This means that LMQL is not specific to any particular text generation model. Instead, we support a wide range of text generation models on the backend, including [OpenAI model](./openai.md), [llama.cpp](./llama.cpp.md) and [HuggingFace Transformers](./hf.md).

## Loading Models

To load models in LMQL, you can use the `lmql.model(...)` function which gives you an [`lmql.LLM`](../lib/generations.md#lmql-llm-objects) object:

```lmql
lmql.model("openai/gpt-3.5-turbo-instruct") # OpenAI API model
lmql.model("random", seed=123) # randomly sampling model
lmql.model("llama.cpp:<YOUR_WEIGHTS>.bin") # llama.cpp model

lmql.model("local:gpt2") # load a `transformers` model in-process
lmql.model("local:gpt2", cuda=True, load_in_4bit=True) # load a `transformers` model in process with additional arguments
lmql.model("gpt2") # access a `transformers` model hosted via `lmql serve-model`
```

LMQL supports multiple inference backends, each of which has its own set of parameters. For more details on how to use and configure the different backends, please refer to one of the following sections:

* [Transformers](./hf.html)
* [llama.cpp](./llama.cpp.html)
* [OpenAI](./openai.html)
* [Azure OpenAI](./azure.html)
* [Replicate](./replicate.html)

## Specifying The Model

After creating an `lmql.LLM` object, you can pass it to a query program to specify the model to use during execution. There are two ways to do this:

### Option A: Specifying the Model Externally

You can specify the model and its parameters externally, i.e. separately from the actual program code:

 
```lmql
import lmql

# uses 'chatgpt' by default
@lmql.query(model="chatgpt")
def tell_a_joke():
    '''lmql
    """A great good dad joke. A indicates the punchline
    Q:[JOKE]
    A:[PUNCHLINE]""" where STOPS_AT(JOKE, "?") and \
                           STOPS_AT(PUNCHLINE, "\n")
    '''

tell_a_joke() # uses chatgpt
tell_a_joke(model=lmql.model("openai/text-davinci-003")) # uses text-davinci-003
```

Here, the `tell_a_joke` query will use ChatGPT by default, but can still be configured to use a different model by passing it as an argument to the query function on invocation.

### Option B: Queries with `from` Clause

You can specify the model as part of the query itself. For this, you can use `from` in combination with the indented syntax. This can be particularly useful, if your choice of model is intentional and should be part of your program.

```lmql
argmax
    "This is a query with a specified 'from'-clause: [RESPONSE]"
from
    "openai/text-ada-001"
```

Here, we specify `"openai/text-ada-001"` directly, but the shown snippet is equivalent to the use of `lmql.model(...)`, i.e. `lmql.model("openai/text-ada-001")`. 

Note, that the `from` keyword is only available with the indented standalone syntax as shown here, where the decoder keywords has to be provided explicitly.


## Playground

To specify the model when running in the playground, you can use the model dropdown available in the top right of the program editor, to set and override the `model` parameter of your query program:

<figure align="center" style="width: 70%; margin: auto;" alt="Screenshot of the model dropdown in the playground">
    <img src="https://github.com/eth-sri/lmql/assets/17903049/5ba2ffdd-e64d-465c-85be-5d9dc2ab6c14">
    <figcaption>Model selection dropdown in the LMQL Playground.</figcaption>
</figure>

## Adding New Model Backends

Due to the modular design of LMQL, it is easy to add support for new models and backends. If you would like to propose or add support for a new model API or inference engine, please reach out to us via our [Community Discord](https://discord.com/invite/7eJP4fcyNT) or via [hello@lmql.ai](mailto:hello@lmql.ai).