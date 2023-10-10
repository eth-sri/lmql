---
order: 2
---
# llama.cpp

LMQL also supports [llama.cpp](https://github.com/ggerganov/llama.cpp) as an inference backend, which can run efficiently on CPU-only and mixed CPU/GPU systems.

Before using llama.cpp models, make sure you installed its Python bindings via `pip install llama-cpp-python` in the same environment where you installed LMQL. You also need the `sentencepiece` or `transformers` package installed, for tokenization.


Also make sure you first convert your model weights according to the [llama.cpp documentation](https://github.com/ggerganov/llama.cpp#prepare-data--run), to the `.bin` format.

Just like [Transformers models](./hf.html), you can load llama.cpp models either locally or via a long-lived `lmql serve-model` inference server.

### Model Server

To start a llama.cpp model server, you can run the following command:

```bash
lmql serve-model llama.cpp:<PATH TO WEIGHTS>.bin
```

This will launch an [LMTP inference endpoint](https://github.com/eth-sri/lmql/tree/main/src/lmql/models/lmtp) on `localhost:8080`, which can be used from LMQL with a query program like this:

```{lmql}
name::llama_remote

argmax 
    "Say 'this is a test':[RESPONSE]" 
from 
    "llama.cpp:<PATH TO WEIGHTS>.bin"
where 
    len(TOKENS(RESPONSE)) < 10
```

### Running Without a Model Server

To load the llama.cpp from the Python process that executes your LMQL query, you can use the following syntax:

```{lmql}
name::llama_local

argmax 
    "Say 'this is a test':[RESPONSE]"
from
    "local:llama.cpp:<PATH TO WEIGHTS>.bin"
where 
    len(TOKENS(RESPONSE)) < 10
```

### Configuring the Llama(...) instance

Any parameters passed to `lmql serve-model` and, when running locally, to `lmql.model(...)` will be passed to the `Llama(...)` constructor. 

For example, to configure the `Llama(...)` instance to use an `n_ctx` value of 1024, run:

```bash
lmql serve-model llama.cpp:<PATH TO WEIGHTS>.bin --n_ctx 1024
```

Or, when running locally, you can use `lmql.model("local:llama.cpp:<PATH TO WEIGHTS>.bin", n_ctx=1024)`.

