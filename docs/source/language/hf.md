# Local Models / 🤗 Transformers

LMQL relies on a two-process architecture: One process (long-running) loads the model and provides a simple inference API, and the other process (short-lived) executes the LMQL query. This architecture is particularly useful for locally-hosted models, as the model loading time can be quite long. If you instead want to load the model in-process, see the [In-Process Model Loading](#in-process-model-loading) section below.

**Prerequisites** Before using the HuggingFace Transformers integration, make sure you installed LMQL via `pip install lmql[hf]`. This ensures the dependencies for running local models are installed (e.g. `transformers`).

Next, to start the LMQL inference server, e.g. for the `gpt2-medium` model, run the following command:

```bash
lmql serve-model gpt2-medium --cuda
```

> `--cuda` will load the model on the GPU, if available. If multiple GPUs are available, the model will be distributed across all GPUs. To run with CPU inference, omit the `--cuda` flag.

By default, this exposes the LMQL inference API on port 8080. When serving a model remotely, make sure to tunnel/forward the port to your client machine.

Now, when executing an LMQL query in the playground or via the CLI, you can simply specify e.g. `gpt2-medium`, and the runtime will automatically connect to the model server running on port 8080 to obtain model-generated text.

### Configuration

**Endpoint and Port** By default, local models will be served via port `8080`. To change this, you can specify the port via the `--port` option of the `lmql serve-model` command. On the client side, to connect to a model server running on a different port, you can specify the port as part of `from` clause, e.g. you can 

```{lmql}

name::local-model-gpt2-port
argmax "Hello[WHO]" from lmql.model("gpt2", endpoint="localhost:9999")
```

**Model Configuration** To load a model with custom quantization preferences or other 🤗 Transformers arguments, you can specify additional arguments when running the `lmql serve-model` command. For this, you can specify arbitrary arguments, that will directly be passed to the underyling `AutoModelForCausalLM.from_pretrained(...)` function, as documented in the [🤗 Transformers documentation](https://huggingface.co/transformers/v3.0.2/model_doc/auto.html#transformers.AutoConfig.from_pretrained).

For example, to 

## Model Use without Inference API

If you would like to load the model in-process, without having to execute a separate `lmql serve-model` command, you can do so by specifying `local:` as part of the model name. For example, to load the `gpt2-medium` model in-process, run the following command:

```{lmql}

name::local-model-gpt2
argmax "Hello[WHO]" from "local:gpt2"
```

Alternatively, you can manually instantiate an `lmql.inprocess(...)` model as demonstrated below. This allows you to pass additional flags like `cuda=True`, analogous to the `lmql serve-model` command.

```{lmql}

name::local-model-gpt2-inprocess

argmax(chunk_timeout=10.0)
    "Hello[WHO]"
from
    lmql.inprocess("gpt2", cuda=True)
where
    STOPS_AT(WHO, "\n") and len(TOKENS(WHO)) < 10
```

## Using the Legacy Inference API

By default, LMQL uses the new inference API which should in most cases be more efficient and faster. Internally, this is achieved by relying on a similar interface as the OpenAI integration, but with a backend implementation that uses the HuggingFace Transformers library.

If the older inference API performs better for you, you can re-enable it by specifying `backend="legacy"` as a decoder argument. For example, to use the legacy API with the `gpt2` model, run the following command:

```{lmql}

name::local-model-gpt2
argmax(backend="legacy") "Hello[WHO]" from "gpt2"
```

On the server side, to use the legacy API, add the `--legacy` option to the `lmql serve-model` command.