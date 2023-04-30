<div align="center">
  <a href="https://lmql.ai">
    <img src="https://raw.githubusercontent.com/eth-sri/lmql/web/lmql.svg" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">LMQL</h3>

  <p align="center">
    A query language for programming (large) language models.
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
  </p>
</div>

![https://discord.gg/7eJP4fcyNT](https://img.shields.io/discord/1091288833997410414)

LMQL is a query language for large language models (LLMs). It facilitates LLM interaction by combining the benefits of natural language prompting with the expressiveness of Python. With only a few lines of LMQL code, users can express advanced, multi-part and tool-augmented LM queries, which then are optimized by the LMQL runtime to run efficiently as part of the LM decoding loop.

![lmql-overview](https://user-images.githubusercontent.com/17903049/222918379-84a00b9a-1ef0-45bf-9384-15a20f2874f0.png)

<p align="center">Example of a simple LMQL program.</p>


## Getting Started

To install the latest version of LMQL run the following command with Python >=3.10 installed.

```
pip install lmql
```

**Local GPU Support:** If you want to run models on a local GPU, make sure to install LMQL in an environment with a GPU-enabled installation of PyTorch >= 1.11 (cf. https://pytorch.org/get-started/locally/).

### Running LMQL Programs

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

To setup a `conda` environment for LMQL with GPU support, run the following commands:

```
# prepare conda environment
conda env create -f scripts/conda/requirements-no-gpu.yml -n lmql-no-gpu
conda activate lmql-no-gpu

# registers the `lmql` command in the current shell
source scripts/activate-dev.sh
```
