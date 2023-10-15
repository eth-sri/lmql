---
order: 2
---
# llama.cpp

[llama.cpp](https://github.com/ggerganov/llama.cpp) is also supported as an LMQL inference backend. This allows the use of models packaged as `.gguf` files, which run efficiently in CPU-only and mixed CPU/GPU environments using the llama.cpp C++ implementation.

## Prerequisites

Before using llama.cpp models, make sure you have installed its Python bindings via `pip install llama-cpp-python` in the same environment as LMQL. You also need the `sentencepiece` or `transformers` package installed, for tokenization. For GPU-enabled `llama.cpp` inference, you need to install the `llama-cpp-python` package with the appropriate build flags, as described in its [`README.md`](https://github.com/abetlen/llama-cpp-python#installation-with-hardware-acceleration) file.

## Using llama.cpp Models

Just like [Transformers models](./hf.html), you can load llama.cpp models either locally or via a long-lived `lmql serve-model` inference server.

#### Model Server

To start a llama.cpp model server, use the following command:

```bash
lmql serve-model llama.cpp:<PATH TO WEIGHTS>.gguf
```

This will launch an [LMTP inference endpoint](https://github.com/eth-sri/lmql/tree/main/src/lmql/models/lmtp) on `localhost:8080`, which can be used in LMQL, using a corresponding [`lmql.model(...)`](./index.md) object.


#### Using the `llama.cpp` endpoint

To access a served `llama.cpp` model, you can use an `lmql.model(...)` object with the following client-side configuration:

```{lmql}
lmql.model("llama.cpp:<PATH TO WEIGHTS>.gguf", tokenizer="<tokenizer>")
```

**Model Path** The client-side `lmql.model(...)` identifier must always match the exact server-side `lmql serve-model` GGUF location, even if the path does not exist on the client machine. In this context, it is merely used as a unique identifier for the model.

**Tokenizer** When omitting `tokenizer=...`, LMQL will use the `transformers`-based tokenizer for [`huggyllama/llama-7b`](https://huggingface.co/huggyllama/llama-7b) by default. This works for Llama and Llama-based fine-tuned models, but must be adapted for others. To find a matching tokenizer for your concrete `gguf` file, look up the `transformers` equivalent entry on the [HuggingFace model hub](https://huggingface.co).
Alternatively, you can use [`sentencepiece`](https://github.com/google/sentencepiece) as a tokenization backend. For this, you have to specify the client-side path to a corresponding `tokenizer.model` file.


#### Running Without a Model Server

To load the llama.cpp directly as part of the Python process that executes your query program, you can use the `local:` prefix, followed by the path to the `gguf` file:

```{lmql}
lmql.model("local:llama.cpp:<PATH TO WEIGHTS>.gguf", tokenizer="<tokenizer>")
```

Again, you can omit the `tokenizer=...` argument if you want to use the default tokenizer for [`huggyllama/llama-7b`](https://huggingface.co/huggyllama/llama-7b). If not, you have to specify a tokenizer, as described above.

## Configuring the Llama(...) instance

Any parameters passed to `lmql serve-model` and, when running locally, to `lmql.model(...)` will be passed to the `Llama(...)` constructor. 

For example, to configure the `Llama(...)` instance to use an `n_ctx` value of 1024, run:

```bash
lmql serve-model llama.cpp:<PATH TO WEIGHTS>.bin --n_ctx 1024
```

Or, when running locally, you can use `lmql.model("local:llama.cpp:<PATH TO WEIGHTS>.bin", n_ctx=1024)`.

