# Setting Up a Development Environment

To setup a `conda` environment for local LMQL development with GPU support, run the following commands:

```
# prepare conda environment
conda env create -f scripts/conda/requirements.yml -n lmql
conda activate lmql

# registers the `lmql` command in the current shell
source scripts/activate-dev.sh
```

> **Operating System**: The GPU-enabled version of LMQL was tested to work on Ubuntu 22.04 with CUDA 12.0 and Windows 10 via WSL2 and CUDA 11.7. The no-GPU version (see below) was tested to work on Ubuntu 22.04 and macOS 13.2 Ventura or Windows 10 via WSL2.

## Development without GPU

This section outlines how to setup an LMQL development environment without local GPU support. Note that LMQL without local GPU support only supports the use of API-integrated models like `openai/text-davinci-003`. Please see the OpenAI API documentation (https://platform.openai.com/docs/models/gpt-3-5) to learn more about the set of available models. 

To setup a `conda` environment for LMQL with GPU support, run the following commands:

```
# prepare conda environment
conda env create -f scripts/conda/requirements-no-gpu.yml -n lmql-no-gpu
conda activate lmql-no-gpu

# registers the `lmql` command in the current shell
source scripts/activate-dev.sh
```