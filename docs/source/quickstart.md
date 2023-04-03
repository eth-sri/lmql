# Getting Started

To install the latest version of LMQL run the following command with Python >=3.10 installed.

```
pip install lmql
```

**Local GPU Support:** If you want to run models on a local GPU, make sure to install LMQL in an environment with a GPU-enabled installation of PyTorch >= 1.11 (cf. [https://pytorch.org/get-started/locally/]()). 

## Running LMQL Programs

After installation, you can launch the LMQL playground IDE with the following command:

```
lmql playground
```

> Using the LMQL playground requires an installation of Node.js. If you are in a conda-managed environment you can install node.js via `conda install nodejs=14.20 -c conda-forge`. Otherwise, please see the offical Node.js website https://nodejs.org/en/download/ for instructions how to install it on your system.

This launches a browser-based playground IDE, including a showcase of many exemplary LMQL programs. If the IDE does not launch automatically, go to `http://localhost:3000`.

Alternatively, `lmql run` can be used to execute local `.lmql` files. Note that when using local HuggingFace Transformers models in the Playground IDE or via `lmql run`, you have to first launch an instance of the LMQL Inference API for the corresponding model via the command `lmql serve-model`.

### Configuring OpenAI API Credentials

If you want to use OpenAI models, you have to configure your API credentials. To do so, create a file `api.env` in the active working directory, with the following contents.

```
openai-org: <org identifier>
openai-secret: <api secret>
```

For system-wide configuration, you can also create an `api.env` file at `$HOME/.lmql/api.env` or at the project root of your LMQL distribution (e.g. `src/` in a development copy).