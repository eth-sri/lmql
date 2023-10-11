# Inference Certificates

<div class="subtitle">Trace and reproduce LLM inference results.</div>

An inference certificate is a simple data structure that records essential information needed to reproduce an inference result. Certificates can be generated for any LLM call that happens in a LMQL context.

The primary use case of certificates is to provide a way to document, trace and reproduce LLM inference results by recording the *exact (tokenized) prompts* and information on the *environment and generation parameters*.


## Obtaining Certificates

To obtain a certificate, specify `certificate=True` as an argument to your current generation context (e.g. a query function or `lmql.generate` call). 

This will produce a certificate including all LLM calls made during the execution of the context. Setting `certificate=True` just prints the resulting data structure to the console. To save the certificate to a file, specify a path as the `certificate` argument. 

To illustrate, consider the following code that produces a certificate and saves it to the file `my-certificate.json` in the current working directory:

```python
# define a simple query function
say_hello = lmql.F("Greet the world:[GREETING]")

# call and save certificate
say_hello(certificate="my-certificate.json")
```

::: info Certificate File

```truncated
{
    "name": "say_hello",
    "type": "lmql.InferenceCertificate",
    "lmql.version": "0.999999 (dev) (build on dev, commit dev)",
    "time": "2023-10-02 23:37:55 +0200",
    "events": [
        {
            "name": "openai.Completion",
            "data": {
                "endpoint": "https://api.openai.com/v1/completions",
                "headers": {
                    "Authorization": "<removed>",
                    "Content-Type": "application/json"
                },
                "tokenizer": "<LMQLTokenizer 'gpt-3.5-turbo-instruct' using tiktoken <Encoding 'cl100k_base'>>",
                "kwargs": {
                    "model": "gpt-3.5-turbo-instruct",
                    "prompt": [
                        "Greet the world:"
                    ],
                    "max_tokens": 64,
                    "temperature": 0,
                    "logprobs": 1,
                    "user": "lmql",
                    "stream": true,
                    "echo": true
                },
                "result[0]": "Greet the world:\n\nHello world! It's nice to meet you. I am excited to explore and learn from all the different cultures, people, and experiences you have to offer. Let's make the most of our time together and create meaningful connections. Cheers to new beginnings!"
            }
        },
        {
            "name": "lmql.LMQLResult",
            "data": [
                {
                    "prompt": "Greet the world:\n\nHello world! It's nice to meet you. I am excited to explore and learn from all the different cultures, people, and experiences you have to offer. Let's make the most of our time together and create meaningful connections. Cheers to new beginnings!",
                    "variables": {
                        "GREETING": "\n\nHello world! It's nice to meet you. I am excited to explore and learn from all the different cultures, people, and experiences you have to offer. Let's make the most of our time together and create meaningful connections. Cheers to new beginnings!"
                    },
                    "distribution_variable": null,
                    "distribution_values": null
                }
            ]
        }
    ],
    "metrics": {
        "openai": {
            "requests": 1,
            "batch_size": 1,
            "tokens": 57
        }
    }
}
```

<button class="btn expand" onclick="this.parentElement.classList.toggle('show')">
    Show All
</button>

:::

**Prompts and Generation Parameters** A certificate contains the parameters of all LLM inference calls made during execution. For API-based LLMs, this includes the request headers and parameters, as well as the response. For local LLMs, it includes the tokenized prompt and the exact parameters and configuration used to instantiate the model.  

**Metrics** The certificate also includes basic metrics on the inference calls made. For API-based LLMs, this includes the number of requests made, the batch size and the number of tokens used.

**Environment** The certificate also captures information on the environment, including the LMQL version and the version of the backend libraries in use.

::: warning Redacting Sensitive Information

By default, parameters such as the OpenAI key are removed from inference certificates. Note however, that certificates may still contain sensitive information such as the prompt used for generation or information on the environment. To remove additional fields from the generated certificates, use the `lmql.runtime.tracing.add_extra_redact_keys` function.

:::

## Generating Certificates for Multiple Calls In a Context

To generate a certificate for multiple generations in a given context, the `lmql.traced` context manager can be used:

```python
with lmql.traced("my-context") as t:
    # call a query 
    res1 = say_hello(verbose=True)

    # call lmql.generate
    res2 = lmql.generate_sync("Greet the animals of the world:", max_tokens=10, verbose=True)

    # generate a combined certificate for
    # all calls made in this context
    print(lmql.certificate(t))
```

This produces one certificate for all calls made in the defined context, where each query is represented as a separate item in the list of `children` certificates. Recorded events are are nested in child certificates. Additionally, an aggregated `metrics` object ranging over all (recursive) calls is included in the top-level certificate.

## Certificate Callbacks And Return Values

As an alternative to directly writing certificates to a file, certificates can also be handled via a callback or returned as a function return value.

To specify a callback function that is called with the generated certificate as an argument, specify it as the `certificate=<FCT>` argument.

The callback is provided with a single `certificate` object, which is of type `lmql.InferenceCertificate`. The certificate can be directly serialized to JSON using string conversion, i.e., `str(certificate)`.