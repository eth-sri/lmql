<div align="center">
  <a href="https://lmql.ai">
    <img src="https://raw.githubusercontent.com/eth-sri/lmql/web/lmql.svg" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">LMQL</h3>

  <p align="center">
    A query language for programming (large) language models.
    <br />
    <a href="https://arxiv.org/pdf/2212.06094"><strong>Read The Paper »</strong></a>
    <br />
    <br />
    <a href="https://lmql.ai">Explore Examples</a>
    ·
    <a href="https://lmql.ai/playground">Playground IDE</a>
    ·
    <a href="https://github.com/eth-sri/lmql/issues">Report Bug</a>
    <br/>
    <br/>
    <i>Full Code Release Coming Soon</i>
  </p>
</div>

LMQL is a query language for large language models (LLMs). It facilitates LLM interaction by combining the benefits of natural language prompting with the expressiveness of Python. With only a few lines of LMQL code, users can express advanced, multi-part and tool-augmented LM queries, which then are optimized by the LMQL runtime to run efficiently as part of the LM decoding loop. To illustrate, consider the following LMQL program:

![lmql-overview](https://user-images.githubusercontent.com/17903049/222918379-84a00b9a-1ef0-45bf-9384-15a20f2874f0.png)

<p align="center">
    <a href="https://lmql.ai">Explore More Examples »</a>
</p>

## About LMQL

Large language models have demonstrated outstanding performance on a wide range of tasks such as question answering and code generation. On a high level, given an input, a language model can be used to automatically complete the sequence in a statistically-likely way. Based on this, users prompt these models with language instructions or examples, to implement a variety of downstream tasks. Advanced prompting methods can even imply interaction between the language model, a user, and external tools such as calculators. However, to obtain state-of-the-art performance or adapt language models for specific tasks, complex task- and model-specific programs have to be implemented, which may still require ad-hoc interaction.

Based on this, we present the novel idea of Language Model Programming (LMP). LMP generalizes language model prompting from pure text prompts to an intuitive combination of text prompting and scripting. Additionally, LMP allows constraints to be specified over the language model output. This enables easy adaption to many tasks, while abstracting language model internals and providing high-level semantics.

To enable LMP, we implement LMQL (short for Language Model Query Language), which leverages the constraints and control flow from an LMP prompt to generate an efficient inference procedure that minimizes the number of expensive calls to the underlying language model.

We show that LMQL can capture a wide range of state-of-the-art prompting methods in an intuitive way, especially facilitating interactive flows that are challenging to implement with existing high-level APIs. Our evaluation shows that we retain or increase the accuracy on several downstream tasks, while also significantly reducing the required amount of computation or cost in the case of pay-to-use APIs.

### Code Release and Stability

We plan to release the LMQL source code soon, together with a packaged release on PyPi. Until then, feel free to experiment with LMQL in the web-based <a href="https://lmql.ai/playground">Playground IDE</a>, which includes the fully-featured LMQL runtime and compiler.

The current version of LMQL should be considered as an alpha release. Please report bugs and feature requests as GitHub Issues.

