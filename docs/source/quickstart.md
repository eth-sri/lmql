# 🚀 Getting Started

## 1. Installation

To get started with LMQL, you can either [install LMQL locally](installation) or use the web-based [Playground IDE](https://lmql.ai/playground), which does not require any local installation.

For the use of self-hosted models via [🤗 Transformers](https://huggingface.co/transformers), you have to install LMQL locally.

## 2. Write Your First Query

A very simple *Hello World* LMQL query looks like this:

```{lmql}

name::hello
argmax "Hello[WHO]" from "openai/text-ada-001" where len(WHO) < 10
```

**Note**: *You can click Open In Playground to run and experiment with this query, directly in your browser.*

We can identify four main clauses in this program:

1. **Decoder Clause** `argmax`: Here, you specify the decoding algorithm to use for text generation. In this case we use `argmax` decoding. This means the model always greedily chooses the most likely token in each decoding step. To learn more about the different supported decoding algorithms in LMQL, please see [Decoders](./language/decoders.md).

2. **Prompt Clause** `"Hello[WHO]"`: In this part of the program, you specify your prompt. Template variables like `[WHO]` are automatically completed by the model. Apart from simple textual prompts, LMQL also support multi-part and scripted prompts. To learn more, see [Scripted Prompting](./language/scripted_prompts.md).

3. **Model Clause** `from "openai/text-ada-001"`: Here, you specify what model you want to use for text generation. Currently, LMQL supports [OpenAI models](https://platform.openai.com/docs/models), like GPT-3.5 variants, ChatGPT, and GPT-4, as well as self-hosted models via [🤗 Transformers](https://huggingface.co/transformers). For more details, please see [Models](./language/models.md).

4. **Constraint Clause** `where len(WHO) < 10`: In this part of the query, users can specify logical, high-level constraints on the output. LMQL uses novel evaluation semantics for these constraints, to automatically translate character-level constraints like `len(WHO) < 10` to (sub)token masks, that can be eagerly enforced during text generation. To learn more, see [Constraints](./language/constraints.md).

This is only a quick overview of LMQL's features. To learn more, consider reading the more detailed [LMQL Language Overview](./language/overview.md) or directly dive into chapters on [Scripted Prompting](./language/scripted_prompts.md), [Constraints](./language/constraints.md), [Decoders](./language/decoders.md), [Models](./language/models.md), and [Tool Augmentation](./language/functions.md).


## 3. Enjoy

These basic steps should get you started with LMQL. If you need more inspiration before writing your own queries, you can explore the examples included with the [Playground IDE](https://lmql.ai/playground) or showcased on the [LMQL Website](https://lmql.ai/).

If you have any questions and or requests for documentation, please feel free to reach out to us via our [Community Discord](https://discord.com/invite/7eJP4fcyNT), [GitHub Issues](https://github.com/eth-sri/lmql/issues), or [Twitter](https://twitter.com/lmqllang).