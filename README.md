<div align="center">
  <a href="https://lmql.ai">
    <img src="https://raw.githubusercontent.com/eth-sri/lmql/web/lmql.svg" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">LMQL</h3>

  <p align="center">
    A programming language for large language models.
    <br />
    <a href="https://docs.lmql.ai"><strong>Documentation »</strong></a>
    <br />
    <br />
    <a href="https://lmql.ai">Explore Examples</a>
    ·
    <a href="https://lmql.ai/playground">Playground IDE</a>
    ·
    <a href="https://github.com/eth-sri/lmql/issues">Report Bug</a>
    <br/>
    <br/>
    <a href="https://discord.gg/7eJP4fcyNT"><img src="https://img.shields.io/discord/1091288833997410414?style=plastic&logo=discord&color=blueviolet&logoColor=white" height=18/></a>
    <a href="https://badge.fury.io/py/Lmql"><img src="https://badge.fury.io/py/Lmql.svg?cacheSeconds=3600" alt="PyPI version" height=18></a>
  </p>
</div>

LMQL is a programming language for large language models (LLMs) based on a *superset of Python*. LMQL offers a novel way of interweaving traditional programming with the ability to call LLMs in your code. It goes beyond traditional templating languages by integrating LLM interaction natively at the level of your program code. 
## Explore LMQL

An LMQL program reads like standard Python, but top-level strings are interpreted as query strings: They are passed to an LLM, where template variables like `[GREETINGS]` are automatically completed by the model:

```python
"Greet LMQL:[GREETINGS]\n" where stops_at(GREETINGS, ".") and not "\n" in GREETINGS

if "Hi there" in GREETINGS:
    "Can you reformulate your greeting in the speech of \
     victorian-era English: [VIC_GREETINGS]\n" where stops_at(VIC_GREETINGS, ".")

"Analyse what part of this response makes it typically victorian:\n"

for i in range(4):
    "-[THOUGHT]\n" where stops_at(THOUGHT, ".")

"To summarize:[SUMMARY]"
```

Program Output:
<div align="center">
  <img src="https://github.com/eth-sri/lmql/assets/17903049/243176f1-dfd4-4129-a59e-ca3dee068295"/>
  <br/>
</div>

LMQL allows you to express programs that contain both, traditional algorithmic logic, and LLM calls. 
At any point during execution, you can prompt an LLM on program variables in combination with standard natural language prompting, to leverage model reasoning capabilities in the context of your program.

To better control LLM behavior, you can use the `where` keyword to specify constraints and data types of the generated text. This enables guidance of the model's reasoning process, and constraining of intermediate outputs using an [expressive constraint language](https://docs.lmql.ai/en/stable/language/constraints.html).

Beyond this linear form of scripting, LMQL also supports a number of decoding algorithms to execute your program, such as `argmax`, `sample` or even advanced branching decoders like [beam search and `best_k`](https://docs.lmql.ai/en/stable/language/decoders.html). 

Learn more about LMQL by exploring thne **[Example Showcase](https://lmql.ai)**, by running your own programs in our **[browser-based Playground IDE](https://lmql.ai/playground)** or by reading the **[documentation](https://docs.lmql.ai)**.

## Feature Overview

LMQL is designed to make working with language models like OpenAI and 🤗 Transformers more efficient and powerful through its advanced functionality, including multi-variable templates, conditional distributions, constraints, datatypes and control flow.

- [X] **Python Syntax**: Write your queries using [familiar Python syntax](https://docs.lmql.ai/en/stable/language/overview.html), fully integrated with your Python environment (classes, variable captures, etc.)
- [X] **Rich Control-Flow**: LMQL offers full Python support, enabling powerful [control flow and logic](https://docs.lmql.ai/en/stable/language/scripted_prompts.html) in your prompting logic.
- [X] **Advanced Decoding**: Take advantage of advanced decoding techniques like [beam search, best_k, and more](https://docs.lmql.ai/en/stable/language/decoders.html).
- [X] **Powerful Constraints Via Logit Masking**: Apply [constraints to model output](https://docs.lmql.ai/en/stable/language/constraints.html), e.g. to specify token length, character-level constraints, datatype and stopping phrases to get more control of model behavior.
- [X] **Optimizing Runtime:** LMQL leverages speculative execution to enable faster inference, constraint short-circuiting, more efficient token use and [tree-based caching](https://lmql.ai/blog/release-0.0.6.html).
- [X] **Sync and Async API**: Execute hundreds of queries in parallel with LMQL's [asynchronous API](https://docs.lmql.ai/en/stable/python/python.html), which enables cross-query batching.
- [X] **Multi-Model Support**: Seamlessly use LMQL with [OpenAI API, Azure OpenAI, and 🤗 Transformers models](https://docs.lmql.ai/en/stable/language/models.html).
- [X] **Extensive Applications**: Use LMQL to implement advanced applications like [schema-safe JSON decoding](https://github.com/microsoft/guidance#guaranteeing-valid-syntax-json-example-notebook), [algorithmic prompting](https://twitter.com/lbeurerkellner/status/1648076868807950337), [interactive chat interfaces](https://twitter.com/lmqllang/status/1645776209702182917), and [inline tool use](https://lmql.ai/#kv).
- [X] **Library Integration**: Easily employ LMQL in your existing stack leveraging [LangChain](https://docs.lmql.ai/en/stable/python/langchain.html) or [LlamaIndex](https://docs.lmql.ai/en/stable/python/llama_index.html).
- [X] **Flexible Tooling**: Enjoy an interactive development experience with [LMQL's Interactive Playground IDE](https://lmql.ai/playground), and [Visual Studio Code Extension](https://marketplace.visualstudio.com/items?itemName=lmql-team.lmql).
- [X] **Output Streaming**: Stream model output easily via [WebSocket, REST endpoint, or Server-Sent Event streaming](https://github.com/eth-sri/lmql/blob/main/src/lmql/output/).

## Getting Started

To install the latest version of LMQL run the following command with Python ==3.10 installed.

```
pip install lmql
```

**Local GPU Support:** If you want to run models on a local GPU, make sure to install LMQL in an environment with a GPU-enabled installation of PyTorch >= 1.11 (cf. https://pytorch.org/get-started/locally/) and install via `pip install lmql[hf]`.

## Running LMQL Programs

After installation, you can launch the LMQL playground IDE with the following command:

```
lmql playground
```

> Using the LMQL playground requires an installation of Node.js. If you are in a conda-managed environment you can install node.js via `conda install nodejs=14.20 -c conda-forge`. Otherwise, please see the official Node.js website https://nodejs.org/en/download/ for instructions how to install it on your system.

This launches a browser-based playground IDE, including a showcase of many exemplary LMQL programs. If the IDE does not launch automatically, go to `http://localhost:3000`.

Alternatively, `lmql run` can be used to execute local `.lmql` files. Note that when using local HuggingFace Transformers models in the Playground IDE or via `lmql run`, you have to first launch an instance of the LMQL Inference API for the corresponding model via the command `lmql serve-model`.

### Configuring OpenAI API Credentials

If you want to use OpenAI models, you have to configure your API credentials. To do so, create a file `api.env` in the active working directory, with the following contents.

```
openai-org: <org identifier>
openai-secret: <api secret>
```

For system-wide configuration, you can also create an `api.env` file at `$HOME/.lmql/api.env` or at the project root of your LMQL distribution (e.g. `src/` in a development copy).

## Installing the Latest Development Version

To install the latest (bleeding-edge) version of LMQL, you can also run the following command:

```
pip install git+https://github.com/eth-sri/lmql
```

This will install the `lmql` package directly from the `main` branch of this repository. We do not continously test the `main` version, so it may be less stable than the latest PyPI release.

## Setting Up a Development Environment

To setup a `conda` environment for local LMQL development with GPU support, run the following commands:

```
# prepare conda environment
conda env create -f scripts/conda/requirements.yml -n lmql
conda activate lmql

# registers the `lmql` command in the current shell
source scripts/activate-dev.sh
```

> **Operating System**: The GPU-enabled version of LMQL was tested to work on Ubuntu 22.04 with CUDA 12.0 and Windows 10 via WSL2 and CUDA 11.7. The no-GPU version (see below) was tested to work on Ubuntu 22.04 and macOS 13.2 Ventura or Windows 10 via WSL2.

### Development without GPU

This section outlines how to setup an LMQL development environment without local GPU support. Note that LMQL without local GPU support only supports the use of API-integrated models like `openai/text-davinci-003`. Please see the OpenAI API documentation (https://platform.openai.com/docs/models/gpt-3-5) to learn more about the set of available models.

To setup a `conda` environment for LMQL with no GPU support, run the following commands:

```
# prepare conda environment
conda env create -f scripts/conda/requirements-no-gpu.yml -n lmql-no-gpu
conda activate lmql-no-gpu

# registers the `lmql` command in the current shell
source scripts/activate-dev.sh
```
