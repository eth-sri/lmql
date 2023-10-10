---
aside: false
---
# Research

<div class="subtitle">The core publications around LMQL and its implementation.</div>

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
}
.paper p {
    margin: 10pt 0pt;
}
</style>