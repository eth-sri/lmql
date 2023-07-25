metadata:release: 2023-07-25 18:00:00 +0000
metadata:authors: team

# LMQL 0.0.6.6 Released

We just released LMQL *0.0.6.6*. This is a minor update with a couple of smaller fixes and improvements.

* `lmql.F` now supports positional arguments:

```python
greet = lmql.F("Greet {a} and {b}: [GREETING]")

# call with positional arguments
greet("Alice", "Bob") # Greet Alice and Bob: Hello!
# call with keyword arguments
greet(a="Alice", b="Bob") # Greet Alice and Bob: Hello!
```

* We improved the error handling of the `llama.cpp` backend and fixed a bug with model identifier parsing. 

* We also fixed a bug with the LMTP scheduler, where CPU load was high even when no tasks were present. Thanks to community member [@4onen](https://github.com/4onen) for reporting and fixing this!

* Added backend support for `auto_gptq` quantized models, contributed by community member [@meditans](https://github.com/meditans).

* We fixed an issue where for Azure OpenAI models, a dummy configuration `api.env` was needed. See [this issue]() and our [documentation](https://docs.lmql.ai/en/stable/language/azure.html) for details. Thanks to community members Missing and [@hooman-bayer](https://github.com/hooman-bayer) for their feedback and contributions to this.

> **Versioning Note**: 0.0.6.6 is the last release with two leading zeros. Starting with the next release, LMQL will adopt semantic versioning and use a single leading zero, i.e. 0.6.7.