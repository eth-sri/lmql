# LlamaIndex

<div class="subtitle">Leverage LlamaIndex for retrieval-enhanced LMQL queries</div>

LMQL can be used with the [LlamaIndex](https://github.com/jerryjliu/llama_index) python library. To illustrate, this notebook demonstrates how you can query a LlamaIndex data structure as part of an LMQL query.

This enables you to leverage [LlamaIndex's powerful index data structures](https://gpt-index.readthedocs.io/en/latest/guides/primer/index_guide.html), to enrich the reasoning capabilities of an LMQL query with retrieved information from e.g. a text document that you provide.

### Importing Libraries

First, we need to import the required LlamaIndex library. For this make sure llama_index is installed via `pip install llama_index`. Then, you can run the following commands to import the required `lmql` and `llama_index` components.

```lmql
import lmql
from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader, ServiceContext
```
### Load Documents and Build Index

In this example, we want to query the full text of the LMQL research paper for useful information during question answering. For this, we first load documents using LlamaIndex's `SimpleDirectoryReader`, and build a `GPTVectorStoreIndex` (an index that uses an in-memory embedding store).

```lmql
# loads ./lmql.txt, the full text of the LMQL paper
documents = SimpleDirectoryReader('.').load_data() 
service_context = ServiceContext.from_defaults(chunk_size_limit=512)
```
Next, we construct a retrieval index over the full text of the research paper.

```lmql
index = GPTVectorStoreIndex.from_documents(documents, service_context=service_context)
```
### Question Answering by Querying with LlamaIndex

Now that we have an `index` to query, we can employ it during LMQL query execution. Since LMQL is fully integrated with the surrounding python program context, we can simply call `index.query(...)` during query execution to do so:

```lmql
similarity_top_k = 2

@lmql.query(model="openai/gpt-3.5-turbo")
async def index_query(question: str):
    '''lmql
    "You are a QA bot that helps users answer questions.\n"
    
    # ask the question
    "Question: {question}\n"

    # look up and insert relevant information into the context
    response = index.query(question, response_mode="no_text", similarity_top_k=similarity_top_k)
    information = "\n\n".join([s.node.get_text() for s in response.source_nodes])
    "\nRelevant Information: {information}\n"
    
    # generate a response
    "Your response based on relevant information:[RESPONSE]"
    '''
```
Here, we first query the `index` using a given `question` and then process the retrieved document chunks, into an small summary answering `question`, by producing a corresponding `RESPONSE` output, using the ChatGPT, as specified in the `from`-clause of the query.

```lmql
result = await index_query("What is scripted prompting in LMQL?", 
                   output_writer=lmql.stream(variable="RESPONSE"))
```
```output
Scripted prompting in LMQL refers to the ability to specify complex interactions, control flow, and constraints using lightweight scripting and declarative SQL-like elements in the Language Model Query Language (LMQL). This allows users to prompt language models with precise constraints and efficient decoding without requiring knowledge of the LM's internals. LMQL can be used to express a wide variety of existing prompting methods using simple, concise, and vendor-agnostic code. The underlying runtime is compatible with existing LMs and can be supported easily, requiring only a simple change in the decoder logic.
```
