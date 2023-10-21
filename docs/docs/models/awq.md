---
order: 5
---
# AWQ

[AutoAWQ](https://github.com/casper-hansen/AutoAWQ/) is also supported as an LMQL inference backend. This allows the use of models quantized using the [Activation-aware Weight Quantization](https://github.com/mit-han-lab/llm-awq) algorithm, which run efficiently in GPU environments using low bit quantization.

## Prerequisites

Before using AWQ models, make sure you have installed its Python package via [the instructions here](https://github.com/casper-hansen/AutoAWQ/) in the same environment as LMQL. You also need the `sentencepiece` or `transformers` package installed, for tokenization.

## Using AWQ Models

Just like [Transformers models](./hf.html), you can load llama.cpp models either locally or via a long-lived `lmql serve-model` inference server.

#### Model Server

To start an AWQ model server, use the following command:

```bash
lmql serve-model awq:<MODEL LOCATION>
```

where `MODEL LOCATION` is either a HuggingFace repo ('TheBloke/Mistral-7B-OpenOrca-AWQ') or the path to a local directory containing an AWQ model config

This will launch an [LMTP inference endpoint](https://github.com/eth-sri/lmql/tree/main/src/lmql/models/lmtp) on `localhost:8080`, which can be used in LMQL, using a corresponding [`lmql.model(...)`](./index.md) object.


#### Using the `awq` endpoint

To access a served `awq` model, you can use an `lmql.model(...)` object with the following client-side configuration:

```{lmql}
lmql.model("awq:<MODEL LOCATION>", tokenizer="<tokenizer>")
```

**Model Path** The client-side `lmql.model(...)` identifier must always match the exact server-side `lmql serve-model` location, even if the path does not exist on the client machine. In this context, it is merely used as a unique identifier for the model.

**Tokenizer** When omitting `tokenizer=...`, LMQL will use the `transformers`-based tokenizer for [`huggyllama/llama-7b`](https://huggingface.co/huggyllama/llama-7b) by default. This works for Llama and Llama-based fine-tuned models, but must be adapted for others. To find a matching tokenizer for your model, look up the `transformers` equivalent entry on the [HuggingFace model hub](https://huggingface.co).
Alternatively, you can use [`sentencepiece`](https://github.com/google/sentencepiece) as a tokenization backend. For this, you have to specify the client-side path to a corresponding `tokenizer.model` file.


#### Running Without a Model Server

To load the AWQ model directly as part of the Python process that executes your query program, you can use the `local:` prefix, followed by the path to the model directory / repo:

```{lmql}
lmql.model("local:awq:<MODEL LOCATION>", tokenizer="<tokenizer>")
```

Again, you can omit the `tokenizer=...` argument if you want to use the default tokenizer for [`huggyllama/llama-7b`](https://huggingface.co/huggyllama/llama-7b). If not, you have to specify a tokenizer, as described above.
