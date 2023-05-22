# 💾 Installation Instructions

> For quick experimentation, you can also use the web-based [Playground IDE](https://lmql.ai/playground)

To install the latest version of LMQL locally, run the following command with Python >=3.10 installed.

```
pip install lmql
```

**Local GPU Support:** If you want to run models on a local GPU, make sure to install LMQL in an environment with a GPU-enabled installation of PyTorch >= 1.11 (cf. [https://pytorch.org/get-started/locally/]()). To install GPU dependencies via pip, install LMQL via `pip install lmql[hf]`.

## Running LMQL Programs

**Playground**

After installation, you can launch a local instance of the Playground IDE using the following command:

```
lmql playground
```

> Using **the LMQL playground requires an installation of Node.js**. If you are in a conda-managed environment you can install node.js via `conda install nodejs=14.20 -c conda-forge`. Otherwise, please see the official [Node.js website](https://nodejs.org/en/download/) for instructions on how to install it on your system.

This launches a browser-based Playground IDE, including a showcase of many exemplary LMQL programs. If the IDE does not launch automatically, go to `http://localhost:3000`.

**Command-Line Interface**

As an alternative to the playground, the command-line tool `lmql run` can be used to execute local `.lmql` files.

**Python Integration**

LMQL can also be used directly from within Python. To use LMQL in Python, you can import the `lmql` package, run query code via `lmql.run` or use a decorator `@lmql.query` for LMQL query functions.

For more details, please see the [Python Integration](./python/python.ipynb) chapter.

## Self-Hosted Models

Note that when using local [🤗 Transformers](https://huggingface.co/transformers) models in the Playground IDE or via `lmql run`, you have to first launch an instance of the LMQL Inference API for the corresponding model via the command `lmql serve-model`. For more details, please see [🤗 Models](./language/hf.md) chapter.

## Configuring OpenAI API Credentials

If you want to use OpenAI models, you have to configure your API credentials. To do so you can either define the `OPENAI_API_KEY` environment variable or create a file `api.env` in the active working directory, with the following contents.

```
openai-org: <org identifier>
openai-secret: <api secret>
```

For system-wide configuration, you can also create an `api.env` file at `$HOME/.lmql/api.env` or at the project root of your LMQL distribution (e.g. `src/` in a development copy).
