# 🤗 Transformers

LMQL relies on a two-process architecture: The inference process (long-running) loads the model and provides an inference API, and the interpreter process (short-lived) executes your LMQL program. This architecture is advantageous for locally-hosted models as the model loading time can be quite long or the required GPU hardware might not be available on the client machine. This chapter first discusses how to use of the two-process inference API, and then presents an alternative on how to leverage [In-Process Model Loading](#in-process-model-loading), which avoids the need for a separate `lmql serve-model` call.

![Inference Architecture](../images/inference.svg)

## As Local Models

**Prerequisites** Before using the local models, make sure you installed LMQL via `pip install lmql[hf]`. This ensures the dependencies for running local models are installed.

Then, to start an LMQL inference process, e.g. for the `gpt2-medium` model, you can run the following command:

```bash
lmql serve-model gpt2-medium --cuda
```

> `--cuda` will load the model on the GPU, if available. If multiple GPUs are available, the model will be distributed across all GPUs. To run with CPU inference, omit the `--cuda` flag. If you only want to use a specific GPU, you can specify the `CUDA_VISIBLE_DEVICES` environment variable, e.g. `CUDA_VISIBLE_DEVICES=0 lmql serve-model gpt2-medium`.

By default, this exposes the LMQL inference API on port 8080. When serving a model remotely, make sure to tunnel/forward the port to your client machine. Now, when executing an LMQL query in the playground or via the CLI, you can simply specify e.g. `gpt2-medium`, and the runtime will automatically connect to the model server running on port 8080 to obtain model-generated text.


### Configuration

**Endpoint and Port** By default, models will be served via port `8080`. To change this, you can specify the port via the `--port` option of the `lmql serve-model` command. On the client side, to connect to a model server running on a different port, you can specify the port as part of `from` clause, e.g.

```{lmql}

name::local-model-gpt2-port
argmax "Hello[WHO]" from lmql.model("gpt2", endpoint="localhost:9999")
```

**Model Configuration** To load a model with custom quantization preferences or other 🤗 Transformers arguments, you can specify additional arguments when running the `lmql serve-model` command. For this, you can specify arbitrary arguments, that will directly be passed to the underyling `AutoModelForCausalLM.from_pretrained(...)` function, as documented in the [🤗 Transformers documentation](https://huggingface.co/transformers/v3.0.2/model_doc/auto.html#transformers.AutoConfig.from_pretrained).

For example, to enable `trust_remote_code` to `True` with the `from_pretrained` function, run the following:

```bash
lmql serve-model gpt2-medium --cuda --port 9999 --trust_remote_code True
```

Alternatively, you can also serve a model directly from within your own Python applications, simply by running `lmql.serve("gpt2-medium", cuda=True, port=9999 trust_remote_code=True)`. Just as with the CLI, standard `transformers` arguments are forwarded to the `from_pretrained` function.

## In-Process Models

If you would like to load the model in-process, without having to execute a separate `lmql serve-model` command, you can do so by specifying instantiating a custom `lmql.model` object with `local:` as part of the model name. For example, to load the `gpt2-medium` model in-process, run the following command:

```{lmql}

name::local-model-gpt2
argmax "Hello[WHO]" from lmql.model("local:gpt2")
```

If you want more control over model loading and configuration, you can pass additional arguments to `lmql.model(...)`, as demonstrated below.

```{lmql}

name::local-model-gpt2-inprocess

import lmql

argmax
    "Hello[WHO]"
from
    lmql.model("local:gpt2", cuda=True)
where
    STOPS_AT(WHO, "\n") and len(TOKENS(WHO)) < 10
```

## Remoting To Replicate

The commercial service [Replicate](https://replicate.com/) can run models uploaded to them in Docker containers in the format constructed by their [Cog](https://github.com/replicate/cog) build tool. Several of these have already been uploaded as public models.

For public models, Replicate only charges for actual GPU time used; for private models, they also charge for startup and idle time. Several models wrapped for LMTP use have already been uploaded publicly, and this repository contains tools to build more.

### Running A 🤗 Model On Replicate

To run a model on Replicate, you need to:

1. Export the environment variable `REPLICATE_API_TOKEN` with the credential to use to authenticate the request.

2. Set the `transport=` argument to your model to `replicate:ORG/MODEL`, matching the name with which the model was uploaded.

3. Set the `tokenizer=` argument to your model to a huggingface transformers name from which correct configuration for the tokenizer in use can be downloaded.

For example:

```lmql
argmax
    """Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.\n
    Q: What is the underlying sentiment of this review and why?\n
    A:[ANALYSIS]\n
    Q: Summarizing the above analysis in a single word -- of the options "positive", "negative", and "neutral" -- how is the review best described?\n
    A:[CLASSIFICATION]"""
from lmql.model(
    # model name is not actually used: endpoint completely overrides model selection
    "meta-llama/llama-2-13b-chat-hf",
    # in this case, uses model from https://replicate.com/charles-dyfis-net/llama-2-13b-hf--lmtp-8bit
    endpoint="replicate:charles-dyfis-net/llama-2-13b-hf--lmtp-8bit",
    # choosing a model with the same tokenizer as meta-llama/llama-2-13b-hf but ungated in huggingface
    tokenizer="lmsys/vicuna-13b-v1.5-16k"
)
where STOPS_AT(ANALYSIS, "\n") and len(TOKENS(ANALYSIS)) < 200
distribution CLASSIFICATION in [" positive", " negative", " neutral"]
```

### Uploading A 🤗 Model To Replicate

Install [Cog](https://github.com/replicate/cog), and see the `scripts/replicate-build` section of the LMQL source tree.

1. Copy `config.toml.example` to `config.toml`, and customize it.

   Change `dest_prefix` to replace `YOURACCOUNT` with the name of the actual Replicate account to which you will be uploading models.

   For each model you wish to build and upload, your config file should have a `[models.MODELNAME]` section, where MODELNAME reflects the name of the model as created on the [Replicate](https://replicate.com/) website.

   `huggingface.repo` should reflect the Hugging Face model name you wish to wrap. If you want to pin a version, also set `huggingface.version`.

   The `config` section may be used to set any values you want to pass in the `model_args` dictionary.

2. Run the `./build` script, with your current working directory being `scripts/replicate-build`.

   This will create a `work/` subdirectory for each model defined in your configuration file.

3. In the `work/MODELNAME` directory, run the generated `./push` script to build and upload your model, or `cog predict` to test your model locally.
