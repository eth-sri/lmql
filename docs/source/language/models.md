# Models

LMQL is a high-level, front-end language for text generation. This means that LMQL is not specific to any particular text generation model. Instead, we support a wide range of text generation models on the backend, including [OpenAI models](https://platform.openai.com/docs/models), as well as self-hosted models via [🤗 Transformers](https://huggingface.co/transformers).

Due to the modular design of LMQL, it is easy to add support for new models and backends. If you would like to propose or add support for a new model API or inference engine, please reach out to us via our [Community Discord](https://discord.com/invite/7eJP4fcyNT) or via [hello@lmql.ai](mailto:hello@lmql.ai).

## OpenAI Models

In general, LMQL supports all models available via the OpenAI Completions or OpenAI Chat API, e.g., GPT-3.5 variants, ChatGPT, and GPT-4.

Specifically, we have tested the following models, with the corresponding model identifier to be used in the LMQL `from` clause:

* `openai/text-ada-001`
* `openai/text-curie-001`
* `openai/text-babbage-001`
* `openai/text-davinci-00[1-3]`

* `openai/gpt-3.5-turbo` also available as `chatgpt`
* `openai/gpt-4` also available as `gpt-4`

### OpenAI API Limitations

Unfortunately, the OpenAI API Completions and Chat API are severely limited in terms of token masking and the availability of the token distribution per predicted token. LMQL tries to leverage these APIs as much as possible, but there are some limitations that we have to work around and may affect users:

* The **OpenAI Completion API limits the number of possible logit biases to 300**. This means, if your constraints induce token masks that are larger than 300 tokens, LMQL will automatically truncate the token mask to the first 300 tokens. This may lead to unexpected behavior, e.g., model performance may be worse than expected as the masks are truncated to be more restrictive than necessary. In cases where the 300 biases limit is exceeded, LMQL prints a warning message to the console, indicating that the logit biases were truncated.

* The **OpenAI Completions API only provides the top-5 logprobs per predicted token**. This means that decoding algorithms that explore e.g. the top-n probabilities to make decisions like beam search, are limited to a branching factor of 5.

* The **OpenAI Chat API does not provide any way to mask tokens or obtain the token distribution (ChatGPT, GPT-4)**. Simple constraints can still be enforced, as the LMQL runtime optimizes them to fit the OpenAI API. However, more complex constraints may not be enforceable. In these cases, LMQL will print a error message to the console. As a workaround users may then adjust their constraints to fit these API limitations or resort to post-processing and backtracking. Scripted prompting, intermediate instructions and simple constraints are still supported with Chat API models, nonetheless.

### Configuring OpenAI API Credentials

If you want to use OpenAI models, you have to configure your API credentials. To do so you can either define the `OPENAI_API_KEY` enviornment variable or create a file `api.env` in the active working directory, with the following contents.

```
openai-org: <org identifier>
openai-secret: <api secret>
```

For system-wide configuration, you can also create an `api.env` file at `$HOME/.lmql/api.env` or at the project root of your LMQL distribution (e.g. `src/` in a development copy).

### Configuring Speculative OpenAI API Use

To integrate the OpenAI API with LMQL, we rely on speculative prediction, where LMQL applies token masking and stopping conditions less eagerly, to save API calls. 

To achieve this, output is generated in chunks, where each chunk is verified to satisfy the constraints before generation continues. The chunk size can be configured by passing `openai_chunksize` parameter in the decoding clause like so:

```{lmql}
name::chunksize

argmax(openai_chunksize=128)
    "The quick brown fox jumps over the[COMPLETION]"
from
    "openai/text-ada-001"
where
    STOPS_AT(COMPLETION, ".")
```

By default, the chunk size is set to 32. This value is chosen based on the consideration, that a very large chunk size means that LMQL potentially has to discard many generated tokens (which is expensive), if a constraint is violated early on. However, if a query has few or only stopping phrase constraints, a larger chunk size may be beneficial for overall query cost. In general, if a query requires multiple long, uninterrupted sequences to be generated without imposing many constraints, a larger chunk size is recommended.

## 🤗 Transformers Models

LMQL also support locally-hosted models via [🤗 Transformers](https://huggingface.co/transformers). This includes all models that are available via the [🤗 Transformers Model Hub](https://huggingface.co/models) and conform to the AutoModelForCausalLM API. Examples include `gpt2` or `facebook/opt-30B`.

The API limitations mentioned above do not apply to locally-hosted models, as the LMQL runtime can leverage the full power of the 🤗 Transformers API and access the full token distribution, enforcing token masks of arbitrary size.

### Running LMQL with 🤗 Transformers

To speed-up turnaround time during query development, LMQL supports a two process architecture. One process (long-running) loads the model and provides a simple inference API, and the other process (short-lived) executes the LMQL query. This architecture is particularly useful for locally-hosted models, as the model loading time can be quite long.

To start a model serving process, e.g. for the `gpt2-medium` model, run the following command:

```bash
lmql serve-model gpt2-medium --cuda
```

> `--cuda` will load the model on the GPU, if available. If multiple GPUs are available, the model will be distributed across all GPUs. To run with CPU inference, omit the `--cuda` flag.

This exposes the LMQL inference API on port 8080. When serving a model remotely, make sure to tunnel/forward the port to your client machine.

Now, when executing an LMQL query in the playground or via the CLI, you can simply specify e.g. `gpt2-medium`, and the runtime will automatically connect to the model server running on port 8080 to obtain model predictions.

#### Running The Playground Remotely

If you would like to run the LMQL Playground itself remotely (e.g. for latency reasons), you can do so using a similar port forwarding/tunnel setup as described above. For this, make sure you client browser has access to the Playground server ports `3000` and `3004`.


