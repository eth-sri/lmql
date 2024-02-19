---
aside: false
---
# Research

<div class="subtitle">The core publications around LMQL and its implementation.</div>

<div class="paper">

## Prompt Sketching for Large Language Models

<span class="venue">
arXiv:2311.04954 [cs.CL]
</span>

<div class="authors">

[Luca Beurer-Kellner](https://www.sri.inf.ethz.ch/people/luca), [Mark Niklas Müller](https://www.sri.inf.ethz.ch/people/mark), [Marc Fischer](https://www.sri.inf.ethz.ch/people/marc), [Martin Vechev](https://www.sri.inf.ethz.ch/people/martin)

</div>

[**SRI**lab](https://www.sri.inf.ethz.ch) @ [ETH Zürich](https://ethz.ch), Switzerland

<a href="https://arxiv.org/abs/2311.04954" class="btn primary pdf">Read the full paper</a>

Many recent prompting strategies for large language models (LLMs) query the model multiple times sequentially – first to produce intermediate results and then the final answer. However, using these methods, both decoder and model are unaware of potential follow-up prompts, leading to disconnected and undesirably wordy intermediate responses. In this work, we address this issue by proposing prompt sketching, a new prompting paradigm in which an LLM does not only respond by completing a prompt, but by predicting values for multiple variables in a template. This way, sketching grants users more control over the generation process, e.g., by providing a reasoning framework via intermediate instructions, leading to better overall results. The key idea enabling sketching with existing, autoregressive models is to adapt the decoding procedure to also score follow-up instructions during text generation, thus optimizing overall template likelihood in inference. Our experiments show that in a zero-shot setting, prompt sketching outperforms existing, sequential prompting schemes such as direct asking or chain-of-thought on 7 out of 8 LLM benchmarking tasks, including state tracking, arithmetic reasoning, and general question answering. To facilitate future use, we release a number of generic, yet effective sketches applicable to many tasks, and an open source library called dclib, powering our sketch-aware decoders.

</div>

<div class="paper">

## Large Language Models are Zero-Shot Multi-Tool Users

<span class="venue">
Knowlege and Logical Reasoning Workshop - ICML 2023, Honolulu, Hawaii
</span>


<div class="authors">

[Luca Beurer-Kellner](https://www.sri.inf.ethz.ch/people/luca), [Marc Fischer](https://www.sri.inf.ethz.ch/people/marc), [Martin Vechev](https://www.sri.inf.ethz.ch/people/martin)

</div>

[**SRI**lab](https://www.sri.inf.ethz.ch) @ [ETH Zürich](https://ethz.ch), Switzerland

<a href="https://files.sri.inf.ethz.ch/website/papers/lmql_actions.pdf" class="btn primary pdf">Read the full paper</a>


We introduce LMQL Actions, a framework and programming environment to facilitate the implementation of tool-augmented language models (LMs). Concretely, we augment LMs with the ability to call actions (arbitrary Python functions), and experiment with different ways of tool discovery and invocation. We find that, while previous works heavily rely on few-shot prompting to teach tool use, a zero-shot, instruction-only approach is enough to achieve competitive performance. At the same time, LMQL Actions zero-shot approach also offers a much simpler programming interface, not requiring any involved demonstrations. Building on this, we show how LMQL Actions enables LLMs to automatically discover and combine multiple tools to solve complex tasks. Overall, we find that inline tool use as enabled by LMQL Actions, outperforms existing tool augmentation approaches, both in arithmetic reasoning tasks and text-based question answering.

</div>

<div class="paper">

## LMQL Chat: Scripted Chatbot Development

<span class="venue">
Neural Conversational AI Workshop, TEACH - ICML 2023, Honolulu, Hawaii
</span>


<div class="authors">

[Luca Beurer-Kellner](https://www.sri.inf.ethz.ch/people/luca), [Marc Fischer](https://www.sri.inf.ethz.ch/people/marc), [Martin Vechev](https://www.sri.inf.ethz.ch/people/martin)

</div>

[**SRI**lab](https://www.sri.inf.ethz.ch) @ [ETH Zürich](https://ethz.ch), Switzerland

<a href="https://files.sri.inf.ethz.ch/website/papers/lmql_chat.pdf" class="btn primary pdf">Read the full paper</a>


We introduce LMQL Chat, a powerful open-source framework for building interactive systems on top of large language models, making it easy to create conversational agents with features like tool usage, internal reflection or safety constraints.

</div>

<div class="paper"> 

## Prompting Is Programming: A Query Language For Large Language Models

<span class="venue">
44th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI 2023), Orlando, Florida
</span>


<div class="authors">

[Luca Beurer-Kellner](https://www.sri.inf.ethz.ch/people/luca), [Marc Fischer](https://www.sri.inf.ethz.ch/people/marc), [Martin Vechev](https://www.sri.inf.ethz.ch/people/martin)

</div>

[**SRI**lab](https://www.sri.inf.ethz.ch) @ [ETH Zürich](https://ethz.ch), Switzerland

<a href="https://arxiv.org/pdf/2212.06094" class="btn primary pdf">Read the full paper</a>


Large language models have demonstrated outstanding performance on a wide range of tasks such as question answering and code generation. On a high level, given an input, a language model can be used to automatically complete the sequence in a statistically-likely way. Based on this, users prompt these models with language instructions or examples, to implement a variety of downstream tasks. Advanced prompting methods can even imply interaction between the language model, a user, and external tools such as calculators. However, to obtain state-of-the-art performance or adapt language models for specific tasks, complex task- and model-specific programs have to be implemented, which may still require ad-hoc interaction.

Based on this, we present the novel idea of Language Model Programming (LMP). LMP generalizes language model prompting from pure text prompts to an intuitive combination of text prompting and scripting. Additionally, LMP allows constraints to be specified over the language model output. This enables easy adaption to many tasks, while abstracting language model internals and providing high-level semantics.

To enable LMP, we implement LMQL (short for Language Model Query Language), which leverages the constraints and control flow from an LMP prompt to generate an efficient inference procedure that minimizes the number of expensive calls to the underlying language model.

We show that LMQL can capture a wide range of state-of-the-art prompting methods in an intuitive way, especially facilitating interactive flows that are challenging to implement with existing high-level APIs. Our evaluation shows that we retain or increase the accuracy on several downstream tasks, while also significantly reducing the required amount of computation or cost in the case of pay-to-use APIs (26-85% cost savings).

</div>

<style scoped>
.primary.pdf {
    top: 10pt;
    right: 10pt;
    margin: 5pt 0pt;
    display: inline-block;
    text-decoration: none;
}
.primary.pdf:hover {
    background-color: #0069d9;
}
.paper {
    position: relative;
    text-align: justify;
    line-height: 1.0;
}
.paper p {
    margin: 10pt 0pt;
}
</style>