# Development Environment

<div class="subtitle">Getting started with core LMQL development.</div>

## GPU-Enabled Anaconda

To setup a `conda` environment for local LMQL development with GPU support, run the following commands:

```
# prepare conda environment
conda env create -f scripts/conda/requirements.yml -n lmql
conda activate lmql

# registers the `lmql` command in the current shell
source scripts/activate-dev.sh
```

::: info 
**Operating System**: The GPU-enabled version of LMQL was tested to work on Ubuntu 22.04 with CUDA 12.0 and Windows 10 via WSL2 and CUDA 11.7. The no-GPU version (see below) was tested to work on Ubuntu 22.04 and macOS 13.2 Ventura or Windows 10 via WSL2.
:::

## Anaconda Development without GPU

This section outlines how to setup an LMQL development environment without local GPU support. Note that LMQL without local GPU support only supports the use of API-integrated models like `openai/gpt-3.5-turbo-instruct`.

To setup a `conda` environment for LMQL with GPU support, run the following commands:

```
# prepare conda environment
conda env create -f scripts/conda/requirements-no-gpu.yml -n lmql-no-gpu
conda activate lmql-no-gpu

# registers the `lmql` command in the current shell
source scripts/activate-dev.sh
```

## With Nix

If you have [Nix](https://nixos.org/) installed, this can be used to invoke LMQL, even if you don't have any of its dependencies previously installed! We try to test Nix support on ARM-based MacOS and Intel-based Linux; bugfixes and contributions for other targets are welcome.

Most targets within the flake have several variants:

- default targets (`nix run github:eth-sri/lmql#playground`, `nix run github:eth-sri/lmql#python`, `nix run github:eth-sri/lmql#lmtp-server`, `nix develop github:eth-sri/lmql#lmql`) download all optional dependencies for maximum flexibility; these are also available with the suffix `-all` (`playground-all`, `python-all`, `lmtp-server-all`).
- `-basic` targets only support OpenAI (and any future models that require no optional dependencies).
- `-hf` targets only support OpenAI and Hugging Face models.
- `-replicate` targets are only guaranteed to support Hugging Face models remoted via Replicate. (In practice, at present, they may also support local Hugging Face models; but this is subject to change).
- `-llamaCpp` targets are only guaranteed to support llama.cpp. (In practice, again, Hugging Face may be available as well).

In all of these cases, `github:eth-sri/lmql` may be replaced with a local filesystem path; so if you're inside a checked-out copy of the LMQL source tree, you can use `nix run .#playground` to run the playground/debugger from that tree.
