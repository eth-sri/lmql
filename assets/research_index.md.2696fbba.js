import{_ as a,o as e,c as t,Q as r}from"./chunks/framework.980cae92.js";const m=JSON.parse('{"title":"Research","description":"","frontmatter":{"aside":false},"headers":[],"relativePath":"research/index.md","filePath":"research/index.md"}'),n={name:"research/index.md"},o=r('<h1 id="research" tabindex="-1" data-v-34af5329>Research <a class="header-anchor" href="#research" aria-label="Permalink to &quot;Research&quot;" data-v-34af5329>​</a></h1><div class="subtitle" data-v-34af5329>The core publications around LMQL and its implementation.</div><div class="paper" data-v-34af5329><h2 id="prompt-sketching-for-large-language-models" tabindex="-1" data-v-34af5329>Prompt Sketching for Large Language Models <a class="header-anchor" href="#prompt-sketching-for-large-language-models" aria-label="Permalink to &quot;Prompt Sketching for Large Language Models&quot;" data-v-34af5329>​</a></h2><span class="venue" data-v-34af5329> arXiv:2311.04954 [cs.CL] </span><div class="authors" data-v-34af5329><p data-v-34af5329><a href="https://www.sri.inf.ethz.ch/people/luca" target="_blank" rel="noreferrer" data-v-34af5329>Luca Beurer-Kellner</a>, <a href="https://www.sri.inf.ethz.ch/people/mark" target="_blank" rel="noreferrer" data-v-34af5329>Mark Niklas Müller</a>, <a href="https://www.sri.inf.ethz.ch/people/marc" target="_blank" rel="noreferrer" data-v-34af5329>Marc Fischer</a>, <a href="https://www.sri.inf.ethz.ch/people/martin" target="_blank" rel="noreferrer" data-v-34af5329>Martin Vechev</a></p></div><p data-v-34af5329><a href="https://www.sri.inf.ethz.ch" target="_blank" rel="noreferrer" data-v-34af5329><strong data-v-34af5329>SRI</strong>lab</a> @ <a href="https://ethz.ch" target="_blank" rel="noreferrer" data-v-34af5329>ETH Zürich</a>, Switzerland</p><p data-v-34af5329><a href="https://arxiv.org/abs/2311.04954" class="btn primary pdf" data-v-34af5329>Read the full paper</a></p><p data-v-34af5329>Many recent prompting strategies for large language models (LLMs) query the model multiple times sequentially – first to produce intermediate results and then the final answer. However, using these methods, both decoder and model are unaware of potential follow-up prompts, leading to disconnected and undesirably wordy intermediate responses. In this work, we address this issue by proposing prompt sketching, a new prompting paradigm in which an LLM does not only respond by completing a prompt, but by predicting values for multiple variables in a template. This way, sketching grants users more control over the generation process, e.g., by providing a reasoning framework via intermediate instructions, leading to better overall results. The key idea enabling sketching with existing, autoregressive models is to adapt the decoding procedure to also score follow-up instructions during text generation, thus optimizing overall template likelihood in inference. Our experiments show that in a zero-shot setting, prompt sketching outperforms existing, sequential prompting schemes such as direct asking or chain-of-thought on 7 out of 8 LLM benchmarking tasks, including state tracking, arithmetic reasoning, and general question answering. To facilitate future use, we release a number of generic, yet effective sketches applicable to many tasks, and an open source library called dclib, powering our sketch-aware decoders.</p></div><div class="paper" data-v-34af5329><h2 id="large-language-models-are-zero-shot-multi-tool-users" tabindex="-1" data-v-34af5329>Large Language Models are Zero-Shot Multi-Tool Users <a class="header-anchor" href="#large-language-models-are-zero-shot-multi-tool-users" aria-label="Permalink to &quot;Large Language Models are Zero-Shot Multi-Tool Users&quot;" data-v-34af5329>​</a></h2><span class="venue" data-v-34af5329> Knowlege and Logical Reasoning Workshop - ICML 2023, Honolulu, Hawaii </span><div class="authors" data-v-34af5329><p data-v-34af5329><a href="https://www.sri.inf.ethz.ch/people/luca" target="_blank" rel="noreferrer" data-v-34af5329>Luca Beurer-Kellner</a>, <a href="https://www.sri.inf.ethz.ch/people/marc" target="_blank" rel="noreferrer" data-v-34af5329>Marc Fischer</a>, <a href="https://www.sri.inf.ethz.ch/people/martin" target="_blank" rel="noreferrer" data-v-34af5329>Martin Vechev</a></p></div><p data-v-34af5329><a href="https://www.sri.inf.ethz.ch" target="_blank" rel="noreferrer" data-v-34af5329><strong data-v-34af5329>SRI</strong>lab</a> @ <a href="https://ethz.ch" target="_blank" rel="noreferrer" data-v-34af5329>ETH Zürich</a>, Switzerland</p><p data-v-34af5329><a href="https://files.sri.inf.ethz.ch/website/papers/lmql_actions.pdf" class="btn primary pdf" data-v-34af5329>Read the full paper</a></p><p data-v-34af5329>We introduce LMQL Actions, a framework and programming environment to facilitate the implementation of tool-augmented language models (LMs). Concretely, we augment LMs with the ability to call actions (arbitrary Python functions), and experiment with different ways of tool discovery and invocation. We find that, while previous works heavily rely on few-shot prompting to teach tool use, a zero-shot, instruction-only approach is enough to achieve competitive performance. At the same time, LMQL Actions zero-shot approach also offers a much simpler programming interface, not requiring any involved demonstrations. Building on this, we show how LMQL Actions enables LLMs to automatically discover and combine multiple tools to solve complex tasks. Overall, we find that inline tool use as enabled by LMQL Actions, outperforms existing tool augmentation approaches, both in arithmetic reasoning tasks and text-based question answering.</p></div><div class="paper" data-v-34af5329><h2 id="lmql-chat-scripted-chatbot-development" tabindex="-1" data-v-34af5329>LMQL Chat: Scripted Chatbot Development <a class="header-anchor" href="#lmql-chat-scripted-chatbot-development" aria-label="Permalink to &quot;LMQL Chat: Scripted Chatbot Development&quot;" data-v-34af5329>​</a></h2><span class="venue" data-v-34af5329> Neural Conversational AI Workshop, TEACH - ICML 2023, Honolulu, Hawaii </span><div class="authors" data-v-34af5329><p data-v-34af5329><a href="https://www.sri.inf.ethz.ch/people/luca" target="_blank" rel="noreferrer" data-v-34af5329>Luca Beurer-Kellner</a>, <a href="https://www.sri.inf.ethz.ch/people/marc" target="_blank" rel="noreferrer" data-v-34af5329>Marc Fischer</a>, <a href="https://www.sri.inf.ethz.ch/people/martin" target="_blank" rel="noreferrer" data-v-34af5329>Martin Vechev</a></p></div><p data-v-34af5329><a href="https://www.sri.inf.ethz.ch" target="_blank" rel="noreferrer" data-v-34af5329><strong data-v-34af5329>SRI</strong>lab</a> @ <a href="https://ethz.ch" target="_blank" rel="noreferrer" data-v-34af5329>ETH Zürich</a>, Switzerland</p><p data-v-34af5329><a href="https://files.sri.inf.ethz.ch/website/papers/lmql_chat.pdf" class="btn primary pdf" data-v-34af5329>Read the full paper</a></p><p data-v-34af5329>We introduce LMQL Chat, a powerful open-source framework for building interactive systems on top of large language models, making it easy to create conversational agents with features like tool usage, internal reflection or safety constraints.</p></div><div class="paper" data-v-34af5329><h2 id="prompting-is-programming-a-query-language-for-large-language-models" tabindex="-1" data-v-34af5329>Prompting Is Programming: A Query Language For Large Language Models <a class="header-anchor" href="#prompting-is-programming-a-query-language-for-large-language-models" aria-label="Permalink to &quot;Prompting Is Programming: A Query Language For Large Language Models&quot;" data-v-34af5329>​</a></h2><span class="venue" data-v-34af5329> 44th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI 2023), Orlando, Florida </span><div class="authors" data-v-34af5329><p data-v-34af5329><a href="https://www.sri.inf.ethz.ch/people/luca" target="_blank" rel="noreferrer" data-v-34af5329>Luca Beurer-Kellner</a>, <a href="https://www.sri.inf.ethz.ch/people/marc" target="_blank" rel="noreferrer" data-v-34af5329>Marc Fischer</a>, <a href="https://www.sri.inf.ethz.ch/people/martin" target="_blank" rel="noreferrer" data-v-34af5329>Martin Vechev</a></p></div><p data-v-34af5329><a href="https://www.sri.inf.ethz.ch" target="_blank" rel="noreferrer" data-v-34af5329><strong data-v-34af5329>SRI</strong>lab</a> @ <a href="https://ethz.ch" target="_blank" rel="noreferrer" data-v-34af5329>ETH Zürich</a>, Switzerland</p><p data-v-34af5329><a href="https://arxiv.org/pdf/2212.06094" class="btn primary pdf" data-v-34af5329>Read the full paper</a></p><p data-v-34af5329>Large language models have demonstrated outstanding performance on a wide range of tasks such as question answering and code generation. On a high level, given an input, a language model can be used to automatically complete the sequence in a statistically-likely way. Based on this, users prompt these models with language instructions or examples, to implement a variety of downstream tasks. Advanced prompting methods can even imply interaction between the language model, a user, and external tools such as calculators. However, to obtain state-of-the-art performance or adapt language models for specific tasks, complex task- and model-specific programs have to be implemented, which may still require ad-hoc interaction.</p><p data-v-34af5329>Based on this, we present the novel idea of Language Model Programming (LMP). LMP generalizes language model prompting from pure text prompts to an intuitive combination of text prompting and scripting. Additionally, LMP allows constraints to be specified over the language model output. This enables easy adaption to many tasks, while abstracting language model internals and providing high-level semantics.</p><p data-v-34af5329>To enable LMP, we implement LMQL (short for Language Model Query Language), which leverages the constraints and control flow from an LMP prompt to generate an efficient inference procedure that minimizes the number of expensive calls to the underlying language model.</p><p data-v-34af5329>We show that LMQL can capture a wide range of state-of-the-art prompting methods in an intuitive way, especially facilitating interactive flows that are challenging to implement with existing high-level APIs. Our evaluation shows that we retain or increase the accuracy on several downstream tasks, while also significantly reducing the required amount of computation or cost in the case of pay-to-use APIs (26-85% cost savings).</p></div>',6),i=[o];function s(l,h,d,p,c,f){return e(),t("div",null,i)}const u=a(n,[["render",s],["__scopeId","data-v-34af5329"]]);export{m as __pageData,u as default};