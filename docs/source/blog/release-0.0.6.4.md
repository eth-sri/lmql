metadata:release: 2023-06-08 18:00:00 +0000
metadata:authors: team

# Releasing LMQL 0.0.6.4: LMTP, Azure, Synchronous API, and more

Among many things, this update contains several bug fixes and improvements. The most notable changes are:

* **Azure OpenAI support** LMQL now supports OpenAI models that are served via Azure. For more information on how to use Azure models, please see the corresponding chapter in the [documentation](https://docs.lmql.ai/en/stable/language/azure.html). Many thanks to [@veqtor](https://github.com/veqtor) for contributing this feature.

* **Local Models via the Language Model Transport Protocol** LMQL 0.0.6.4 implements a novel protocol to stream token output from local models, vastly improving performance. In our first benchmarks, we observed a 5-6x speedup for local model inference. For more information on how to use local models, please see the corresponding chapter in the [documentation](https://docs.lmql.ai/en/stable/language/hf.html).

   To learn more about the internals of the new streaming protocol, i.e. the language model transport protocol (LMTP), you can find more details in [this README file](https://github.com/eth-sri/lmql/blob/main/src/lmql/models/lmtp/README.md). In the future, we intend to implement more model backends using LMTP, streamlining communication between LMQL and models.

   <div style="text-align:center">
    <img src="https://docs.lmql.ai/en/stable/_images/inference.svg" width="80%" />
    <br>
    <i>LMQL's new streaming protocol (LMTP) allows for faster local model inference.</i>
   </div>

* **Synchronous Python API** Next to an `async/await` based API, LMQL now also provides a synchronous API. This means you no longer need to use `asyncio` to use LMQL from Python. 

    To use the synchronous API, simply declare `@lmql.query` function without the `async` keyword, e.g.

    ```python
    import lmql

    @lmql.query
    def hello(s: str):
        '''lmql
        argmax 
            "Hello {s} [RESPONSE]" 
            return RESPONSE
        from 
            "chatgpt"
        '''

    print(hello("world")) # ['Hello! How can I assist you today?']
    ```

    If you instead want to use `lmql.run` in a synchronous context, you can now use `lmql.run_sync` instead. To learn more about how LMQL can be used from Python, check out our [documentation](https://docs.lmql.ai/en/stable/python/python.html).

* **Improved Tokenizer Backends** LMQL can now use the excellent [`tiktoken` tokenizer](https://github.com/openai/tiktoken) as tokenization backend (for OpenAI models). Furthermore, all tokenization backends have been ported to operate on a byte-level, which improves support for multibyte characters and emojis. This is especially relevant for non-English languages and special characters.

* **Docker Image** LMQL now provides a Docker image that can be used to run the LMQL playground in a containerized environment. For more information, please see the [documentation](https://docs.lmql.ai/en/stable/docker-setup.html). Many thanks to [@SilacciA](https://github.com/SilacciA) for contributing this feature.

* **Faster Startup Time** We optimized LMQL's import hierarchy, which results in faster module loading time.