# Testing

**Running Test Suites** The directory contains a number of test suites. To run all tests, execute `python src/lmql/tests/all.py`. Note that for some tests you need to configure an OpenAI API key according to the instructions in documentation. We are working to remove the external dependency on the OpenAI API, but for now it is still required for some tests.

**Adding Tests** You are also invited to add new tests in the form of a new `test_*.py` file in the `src/lmql/tests/` directory. For an example of how to write tests, please see the e.g. https://github.com/eth-sri/lmql/blob/main/src/lmql/tests/test_nested_queries.py. As demonstrated by this file, also try to implement your tests using lmql.model("random", seed=<SEED>) to make sure your test code can be run without actually using an LLM or external API, and that it can be re-run deterministically.

## Running Tests in Docker

To run the tests in a Docker container, first build the `Dockerfile.tests` image at the project root:

```bash
docker build -f Dockerfile.tests -t lmql-tests .
```

Then run the tests in the container:

```bash
docker run -v ./src:/lmql/src lmql-tests python src/lmql/tests/all.py [langchain] [openai]
```

This command will test the current working directory, which is mounted to `/lmql/src` in the container.

The `langchain` and `openai` arguments are optional and can be used to explicitly enable or disable the corresponding integration tests with the OpenAI API and LangChain. By default, both are disabled.

## Test Levels and Dependencies

* All files in this directory starting with `test_` are considered *default level* test modules. They are run by default when executing `python src/lmql/tests/all.py` and should not have any OpenAI API or LangChain dependencies. For *default level* tests, small `transformers` models or `llama.cpp` models are used, which can be executed fully locally without the need for an API key.

    For proper functioning, some default level tests may require a quantized variant of *Llama-2 Chat 7b* at `/lmql/llama-2-7b-chat.Q2_K.gguf`, which can be downloaded from `ttps://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q2_K.gguf` and can run on a CPU-only machine.
    
    Run tests with the provided `Dockefile.tests` file to automatically set up the required directory structure in a Docker container.

* Files in subfolders of the `optional/` directory, like `optional/openai/tests_*.py`, are considered *optional level* test modules. They are not executed by default, but can be run by executing e.g. `python src/lmql/tests/all.py openai`. They may have OpenAI API, LangChain or other optional dependencies.