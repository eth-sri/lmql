# 🤗 Transformers

By default, LMQL relies on a two-process architecture: One process (long-running) loads the model and provides a simple inference API, and the other process (short-lived) executes the LMQL query. This architecture is particularly useful for locally-hosted models, as the model loading time can be quite long.

To start a model serving process, e.g. for the `gpt2-medium` model, run the following command:

```bash
lmql serve-model gpt2-medium --cuda
```

> `--cuda` will load the model on the GPU, if available. If multiple GPUs are available, the model will be distributed across all GPUs. To run with CPU inference, omit the `--cuda` flag.

By default, this exposes the LMQL inference API on port 8080. When serving a model remotely, make sure to tunnel/forward the port to your client machine.

Now, when executing an LMQL query in the playground or via the CLI, you can simply specify e.g. `gpt2-medium`, and the runtime will automatically connect to the model server running on port 8080 to obtain model predictions.

## In-Process Model Loading

If you would like to load the model in-process, without having to execute a separate `lmql serve-model` command, you can do so by specifying `local:` as part of the model name. For example, to load the `gpt2-medium` model in-process, run the following command:

```{lmql}

name::local-model-gpt2
argmax "Hello[WHO]" from "local:gpt2"
```

Alternatively, you can manually instantiate a `lmql.inprocess(...)` model as demonstrated below. This allows you to pass additional flags like `cuda=True` as with the `lmql serve-model` command.

```{lmql}

name::local-model-gpt2-inprocess

argmax(chunk_timeout=10.0)
    "Hello[WHO]"
from
    lmql.inprocess("gpt2", cuda=True)
where
    STOPS_AT(WHO, "\n") and len(TOKENS(WHO)) < 10
```