# Getting Started

## 1. Installation

To get started with LMQL, you can either [install LMQL locally](installation) or use the web-based [Playground IDE](https://lmql.ai/playground), which does not require any local installation.

For the use of self-hosted models via [🤗 Transformers](https://huggingface.co/transformers), you have to install LMQL locally.

## 2. Writing Your First Query

A very simple *Hello World* LMQL query looks like this:

```{lmql}

name::hello
argmax "Hello[WHO]" from "openai/text-ada-001" where len(WHO) < 10
```

We can identify different *clauses* in this program:

* **Decoder Clause** `argmax`: Here, you specify the decoding algorithm to use for text generation. In this case we use argmax decoding. This means the model always greedily chooses the most likely token in each decoding step. To learn more about the different supported decoding algorithms, please see [Decoders](./language/decoders.md).

* **Prompt Clause** `"Hello[WHO]"`: In this part of the program, you specify your prompt. Template variables like `[WHO]` are automatically completed by the model. Apart from simple textual prompts, LMQL also support multi-part and scripted prompts. To learn more, see [Scripted Prompting](./language/scripted_prompts.md).

* **Model Clause** `from "openai/text-ada-001"`: Here, you specify what model you want to use for text generation. Currently, LMQL supports [OpenAI models](https://platform.openai.com/docs/models), like GPT-3.5 variants, ChatGPT, and GPT-4, as well as self-hosted models via [🤗 Transformers](https://huggingface.co/transformers). For more details, please see [Models](./language/models.md).

* **Constraint Clause** `where len(WHO) < 10`: In this part of the query, users can specify logical, high-level constraints on the output. LMQL uses novel evaluation sematnics for these constraints, to automatically translate character-level constraints like `len(WHO) < 10` to (sub)token masks, that can be eagerly enforced during text generation. To learn more, see [Constraints](./language/constraints.md).

This is only a brief overview of LMQL's core feature set. To learn more consider reading any of the referenced chapters or the [LMQL research paper](https://arxiv.org/pdf/2212.06094).


## 3. Enjoy

These basic steps should get you started with LMQL. If you need more inspiration before writing your own queries, you can explore the examples included with the [Playground IDE](https://lmql.ai/playground) or showcased on the [LMQL Website](https://lmql.ai/).

If you have any questions and or requests for documentation, please feel to free to reach out to us via our [Community Discord](https://discord.com/invite/7eJP4fcyNT), [GitHub Issues](https://github.com/eth-sri/lmql/issues), or [Twitter](https://twitter.com/lmqllang).