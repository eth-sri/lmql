# 🚀 Getting Started

## 1. Installation

To get started with LMQL, you can either [install LMQL locally](installation) or use the web-based [Playground IDE](https://lmql.ai/playground), which does not require any local installation.

For the use of self-hosted models via [🤗 Transformers](language/hf.md) or [llama.cpp](language/llama.cpp.md), you have to install LMQL locally.

## 2. Write Your First Query

A very simple *Hello World* LMQL query looks like this:

```{lmql}

name::hello
"Say 'this is a test':[RESPONSE]" where len(RESPONSE) < 25

model-output::
Say 'this is a test': [RESPONSE This is a test.]
```

**Note**: *You can click Open In Playground to run and experiment with this query, directly in your browser.*

This simple LMQL program consists of a single prompt statement and an associated `where` clause:

- **Prompt Statement** `"Say 'this is a test'[RESPONSE]"`: Prompts are constructed using so-called prompt statements that look like top-level strings in Python. Template variables like `[RESPONSE]` are automatically completed by the model. Apart from single-line textual prompts, LMQL also support multi-part and scripted prompts, e.g. by allowing control flow and branching behavior to control prompt construction. To learn more, see [Scripted Prompting](./language/scripted_prompts.md).

- **Constraint Clause** `where len(RESPONSE) < 10`: In this second part of the statement, users can specify logical, high-level constraints on the output. LMQL uses novel evaluation semantics for these constraints, to automatically translate character-level constraints like `len(RESPONSE) < 25` to (sub)token masks, that can be eagerly enforced during text generation. To learn more, see [Constraints](./language/constraints.md).

## 3. Going Further

Extending on your first query above, you may want to add more complex logic, e.g. by adding a second part to the prompt. Further, you may want to employ a different decoding algorithm, e.g. to sample multiple trajectories of your program or use a different model. 

Let's extend our initial query, to allow for these changes:

```{lmql}
name::hello-extended

sample(temperature=1.2)
    "Say 'this is a test'[RESPONSE]" where len(TOKENS(RESPONSE)) < 25

    if "test" not in RESPONSE:
        "You did not say 'test', try again:[RESPONSE]" where len(TOKENS(RESPONSE)) < 25
    else:
        "Good job"
from
    "openai/text-ada-001"
```

Going beyond what we have seen so far, this LMQL program extends on the above in a few ways:

**Decoder Clause** `sample(temperature=1.2)`: Here, we specify the decoding algorithm to use for text generation. In this case we use `sample` decoding with slightly increased temperature (>1.0). Above, we implicitly relied on deterministic `argmax` decoding, which is the default in LMQL. To learn more about the different supported decoding algorithms in LMQL (e.g. `beam` or `best_k`), please see [Decoders](./language/decoders.md). 

**Prompt Program**: The main body of the program specifies the prompt. As before, we use prompt statements here, however, now we also make use of control-flow and branching behavior.
    
On each LLM call, the concatenation of all prompt statements so far, form the prompt used to generate a value for the currently active template variable like `RESPONSE`. This means the LLM is always aware of the full prompt context so far, when generating a value for a template variable.
    
After a prompt statement has been executed, the contained template variables are automatically exposed to the surrounding program context. This allows you to react to model output and incorporate the results in your program logic. To learn more about this form of interactive prompting, please see [Scripted Prompting](./language/scripted_prompts.md).

**Model Clause** `from "openai/text-ada-001"`: In this extended version we now specify a specific model to use for text generation. LMQL supports [OpenAI models](https://platform.openai.com/docs/models), like GPT-3.5 variants, ChatGPT, and GPT-4, but also self-hosted models, e.g. via [🤗 Transformers](https://huggingface.co/transformers). For more details, please see [Models](./language/models.rst). By default, LMQL relies on `openai/text-davinci-003`, if not specified otherwise.
## 3. Enjoy

These basic steps should get you started with LMQL. If you need more inspiration before writing your own queries, you can explore the examples included with the [Playground IDE](https://lmql.ai/playground) or showcased on the [LMQL Website](https://lmql.ai/).

If you have any questions and or requests for documentation, please feel free to reach out to us via our [Community Discord](https://discord.com/invite/7eJP4fcyNT), [GitHub Issues](https://github.com/eth-sri/lmql/issues), or [Twitter](https://twitter.com/lmqllang).