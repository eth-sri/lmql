# Models

LMQL is a high-level, front-end language for text generation. This means that LMQL is not specific to any particular text generation model. Instead, we support a wide range of text generation models on the backend, including [OpenAI models](https://platform.openai.com/docs/models), as well as self-hosted models via [🤗 Transformers](https://huggingface.co/transformers).

Due to the modular design of LMQL, it is easy to add support for new models and backends. If you would like to propose or add support for a new model API or inference engine, please reach out to us via our [Community Discord](https://discord.com/invite/7eJP4fcyNT) or via [hello@lmql.ai](mailto:hello@lmql.ai).

```{toctree}
:maxdepth: 1

openai.md
azure.md
hf.md
llama.cpp.md
```