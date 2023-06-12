# Comparison with Other Libraries

This chapter compares LMQL with other Python libraries for language model use.

### Comparison with `guidance`

[Guidance](https://github.com/microsoft/guidance) is a templating language for large language models. It is a Python library with 
a Handlebars-like syntax. To highlight the benefits of LMQL and Guidance, we compare across several dimensions:

|  | LMQL | Guidance |
| :--- | :--- | :--- |
| **Language** |  |  |
| *Syntax* | Python Syntax | Handlebars  (`{{...}}`)|
| *Control-Flow* | Full Python Support | Provides (`{{#if ...}`, `{{#each ...}`, ...)|
| *Function Calls* | Call Any Python Function | `{{func <args>}}` where `func` is passed as template parameter |
| *Python Integration* | LMQL programs act as [native Python functions](./python.ipynb#Program-Context) (capture variables, can be class method) | Template function have no access to surrounding program context |
| *Async API* | [Async API](./python.ipynb) allowing you to run hundreds of queries in parallel (including cross-query optimization and batching) | - |
| | | |
| **Decoding** |  |  |
| *sample/argmax* | ✅ | ✅ |
| Advanced decoders (beam search, best_k, var, ...) | [✅ Decoders](../language/decoders.md) | - |
| Multi-Variable Templates | ✅ | ✅ |
| Vary multiple decoders In templates | *In Development* | ✅ |
| Conditional distributions | [✅ `distribution` clause](../language/overview.md#extracting-more-information-with-distributions) | - |
| **Model Support** |  |  |
| *OpenAI API*  | ✅ | ✅ |
| *Azure OpenAI*  | ✅ | ✅ |
| *🤗 Transformers*  | ✅ | ✅ |
| **Constraints** | | |
| Simple Token Length Constraints | ✅ | ✅ |
| RESULT in [a, b, ...] | ✅ | ✅ |
| Character-level constraints (number of words, character length) | ✅ | - |
| Datatype Constraints (e.g. integer only) | ✅ | - |
| Extendible constraint system | ✅ [Formal Semantics + Extendible](../language/constraints.md#custom-constraints-and-theoretical-background) + [[Paper]](https://arxiv.org/pdf/2212.06094) | - |
| **Advanced Applications** | | |
| JSON Decoding | [Type Constraints (Preview Release)](https://next.lmql.ai) and [Internal Implementation](https://github.com/microsoft/guidance#guaranteeing-valid-syntax-json-example-notebook) | [Snippet](https://github.com/microsoft/guidance#guaranteeing-valid-syntax-json-example-notebook)
| Role Tags | [Playground](https://lmql.ai#chat) (ChatGPT only for now) | [Snippet](https://github.com/microsoft/guidance#role-based-chat-model-example-notebook)
| Tool Use | [Calculator](https://lmql.ai/playground?snippet=calc), [Search](https://lmql.ai/playground?snippet=wiki) | [Search](https://github.com/microsoft/guidance/blob/main/notebooks/chat.ipynb)
| Generating Tabular Data | [LMQL and Pandas](./pandas.ipynb) | - |
| Algorithmic Prompting | [LLM-based Sorting Algorithms](https://twitter.com/lbeurerkellner/status/1648076868807950337) | - |
| Interactive Chat Interface | [Chat in the Playground](https://twitter.com/lmqllang/status/1645776209702182917) | - |
| Code Interpreter | [Execute Python Code in LMQL](https://twitter.com/lmqllang/status/1654076825457381376) | - |
| Inline Tool Use | [Calculator](https://lmql.ai/playground?snippet=calc), [Key-Value Storage](https://lmql.ai/#kv) | - |
| **Runtime Optimization** | | |
| Tree-based Token Caching | ✅ [(Blog)](https://lmql.ai/blog/release-0.0.6.html) | - |
| Transformers Key-Value Caching | *In Development* | ✅ ([`guidance` acceleration](https://github.com/microsoft/guidance#guidance-acceleration-notebook)) |
| Cache Persistence across multiple runs | ✅ [(Blog)](https://lmql.ai/blog/release-0.0.6.html#persisting-the-cache) | - |
| Token Healing | *In Development* | [✅](https://github.com/microsoft/guidance#token-healing-notebook) |
| Eager Constraint Evaluation and Short-Circuiting | ✅ [(Blog)](https://lmql.ai/blog/release-0.0.6.html#short-circuiting-long-constraints) | - |
| **Library Integration** | | |
| Langchain | LMQL queries can be used seamlessly as [LangChain `Chain` objects](./langchain.ipynb#Using-LMQL-from-LangChain) | - |
| LlamaIndex | LMQL can directly call and leverage [LlamaIndex data structures during decoding](./llama_index.ipynb) | - |
| **Tooling** | | |
| *Interactive Use* | ✅ Interactive [Playground IDE](https://lmql.ai/playground) with visual decoding tree and editor | ✅ Jupyter Notebook Integration |
| *Visual Studio Code* | [✅ Extension](https://marketplace.visualstudio.com/items?itemName=lmql-team.lmql) | - |
| **Output (Streaming)** | | |
| Streaming Model Output | ✅ | ✅ |
| `websocket` streaming | [✅ GitHub](https://github.com/eth-sri/lmql/blob/main/src/lmql/output/ws.py) | - |
| REST endpoint | [✅ GitHub](https://github.com/eth-sri/lmql/blob/main/src/lmql/output/http.py) | - |
| Server-Sent Event streaming | [✅ GitHub](https://github.com/eth-sri/lmql/blob/main/src/lmql/output/sse.py) | - |
