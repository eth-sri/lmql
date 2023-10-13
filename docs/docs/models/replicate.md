# Replicate

[Replicate](https://replicate.com/) is a commercial service that can run models uploaded to them in Docker containers, in the format constructed by their [Cog](https://github.com/replicate/cog) build tool. Several of these have already been uploaded as public models.

For public models, Replicate only charges for actual GPU time used; for private models, they also charge for startup and idle time. Several models wrapped for LMQL/LMTP use have already been uploaded publicly, and this chapter documents how to build, operate and deploy more.

## Running A 🤗 Transformers Model On Replicate

To run a [🤗 Transformers](./hf.html) model on Replicate, you need to:

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
    "meta-llama/Llama-2-13b-chat-hf",
    # in this case, uses model from https://replicate.com/charles-dyfis-net/llama-2-13b-hf--lmtp-8bit
    endpoint="replicate:charles-dyfis-net/llama-2-13b-hf--lmtp-8bit",
    # choosing a model with the same tokenizer as meta-llama/Llama-2-13b-hf but ungated in huggingface
    tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded",
)
where STOPS_AT(ANALYSIS, "\n") and len(TOKENS(ANALYSIS)) < 200
distribution CLASSIFICATION in [" positive", " negative", " neutral"]
```

## Uploading A 🤗 Model To Replicate

You can also upload and deploy your own LMQL models to Replicate. To do so, first install [Cog](https://github.com/replicate/cog). In addition to that, LMQL provides scripts that largely automate the process of building and uploading models (see the `scripts/replicate-build` section of the LMQL source distribution).

1. Create a corresponding model on the [Replicate](https://replicate.com/) website.

2. Copy `config.toml.example` to `config.toml`, and customize it.

   Change `dest_prefix` to replace `YOURACCOUNT` with the name of the actual Replicate account to which you will be uploading models.

   For each model you wish to build and upload, your config file should have a `[models.MODELNAME]` section. Make sure MODELNAME reflects the name of the model as create in your Replicate account.

   `huggingface.repo` should reflect the Hugging Face model name you wish to wrap. If you want to pin a version, also set `huggingface.version`.

   The `config` section may be used to set any values you want to pass in the `model_args` dictionary.

3. Run the `./build` script, with your current working directory being `scripts/replicate-build`.

   This will create a `work/` subdirectory for each model defined in your configuration file.

4. In the `work/MODELNAME` directory, run the generated `./push` script to build and upload your model, or `cog predict` to test your model locally.
