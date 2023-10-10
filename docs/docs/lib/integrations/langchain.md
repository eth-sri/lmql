# LangChain

<div class="subtitle">Leverage your LangChain stack with LMQL</div>

LMQL can also be used together with the [🦜🔗 LangChain](https://python.langchain.com/en/latest/index.html#) python library. Both, using langchain libraries from LMQL code and using LMQL queries as part of chains are supported.

## Using LangChain from LMQL

We first consider the case, where one may want to use LangChain modules as part of an LMQL program. In this example, we want to leverage the LangChain `Chroma` retrieval model, to enable question answering about a text document (the LMQL paper in this case).

First, we need to import the required libraries.

```lmql
import lmql
import asyncio
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
```
Next, we load and embed the text of the relevant document (`lmql.txt` in our case).

```lmql
# load text of LMQL paper
with open("lmql.txt") as f:
    contents = f.read()
texts = []
for i in range(0, len(contents), 120):
    texts.append(contents[i:i+120])

embeddings = OpenAIEmbeddings()
docsearch = Chroma.from_texts(texts, embeddings, 
    metadatas=[{"text": t} for t in texts], persist_directory="lmql-index")
```
We then construct a chatbot function, using a simple LMQL query, that first prompts the user for a question via `await input(...)`, retrieves relevant text paragraphs using LangChain and then produces an answer using `openai/gpt-3.5-turbo` (ChatGPT).

```lmql
import termcolor

@lmql.query(model="openai/gpt-3.5-turbo")
async def chatbot():
    '''lmql
    # system instruction
    """{:system} You are a chatbot that helps users answer questions.
    You are first provided with the question and relevant information."""
    
    # chat loop
    while True:
        # process user input
        q = await input("\nQuestion: ")
        if q == "exit": break
        # expose question to model
        "{:user} {q}\n"
        
        # insert retrieval results
        print(termcolor.colored("Reading relevant pages...", "green"))
        results = set([d.page_content for d in docsearch.similarity_search(q, 4)])
        information = "\n\n".join(["..." + r + "..." for r in list(results)])
        "{:system} \nRelevant Information: {information}\n"
        
        # generate model response
        "{:assistant} [RESPONSE]"
    '''

await chatbot(output_writer=lmql.stream(variable="RESPONSE"))
```
```promptdown
# Chat Log
[bubble:system| You are a chatbot that helps users answer questions. 
You are first provided with the question and relevant information.]
[bubble:user| What is LMQL?]
[bubble:system| Relevant Information: (inserted by retriever)]
[bubble:assistant| LMQL is a high-level query language for LMs that allows for great expressiveness and supports scripted prompting.]
[bubble:user| How to write prompts?]
[bubble:system| Relevant Information: (inserted by retriever)]
[bubble:assistant| To write prompts, you can use a language model to expand the prompt and obtain the answer to a specific question.]
```

As shown in the query, inline LMQL code appearing in a Python script can access the outer scope containing e.g. the `docsearch` variable, and access any relevant utility functions and object provided by LangChain.

For more details on building Chat applications with LMQL, see the [Chat API documentation](../chat.md)

## Using LMQL from LangChain

In addition to using langchain utilities in LMQL query code, LMQL queries can also seamlessly be integrated as a `langchain` `Chain` component. 

For this consider, the sequential prompting example from the `langchain` documentation, where we first prompt the language model to propose a company name for a given product, and then ask it for a catchphrase.

To get started, we first import the relevant langchain components, as well as LMQL.

```lmql
from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (ChatPromptTemplate,HumanMessagePromptTemplate)
from langchain.llms import OpenAI

import lmql
```
Our chain has two stages: (1) Asking the model for a company name, and (2) asking the model for a catchphrase. For the sake of this example, we will implement (1) in with a langchain prompt and (2) with an LMQL query. 

First, we define the langchain prompt for the company name and instantiate the resulting `LLMChain`:

```lmql
# setup the LM to be used by langchain
llm = OpenAI(temperature=0.9)

human_message_prompt = HumanMessagePromptTemplate(
        prompt=PromptTemplate(
            template="What is a good name for a company that makes {product}?",
            input_variables=["product"],
        )
    )
chat_prompt_template = ChatPromptTemplate.from_messages([human_message_prompt])
chat = ChatOpenAI(temperature=0.9)
chain = LLMChain(llm=chat, prompt=chat_prompt_template)
```
This can already be executed to produce a company name:

```lmql
chain.run("colorful socks")
```
```result
'VibrantSock Co.\nColorSplash Socks\nRainbowThreads\nChromaSock Co.\nKaleidosocks\nColorPop Socks\nPrismStep\nSockMosaic\nHueTrend Socks\nSpectrumStitch\nColorBurst Socks'
```
Next, we define prompt (2) in LMQL, i.e. the LMQL query generating the catchphrase:

```lmql
@lmql.query(model="chatgpt")
async def write_catch_phrase(company_name: str):
    '''
    "Write a catchphrase for the following company: {company_name}. [catchphrase]"
    '''
```
Again, we can run this part in isolation, like so:

```lmql
(await write_catch_phrase("Socks Inc")).variables["catchphrase"]
```
```result
' "Step up your style with Socks Inc. - where comfort meets fashion!"'
```
To chain the two prompts together, we can use a `SimpleSequentialChain` from `langchain`. To make an LMQL query compatible for use with `langchain`, just call `.aschain()` on it, before passing it to the `SimpleSequentialChain` constructor.

```lmql
from langchain.chains import SimpleSequentialChain
overall_chain = SimpleSequentialChain(chains=[chain, write_catch_phrase.aschain()], verbose=True)
```
Now, we can run the overall chain, relying both on LMQL and langchain components:

```lmql
# Run the chain specifying only the input variable for the first chain.
catchphrase = overall_chain.run("colorful socks")
print(catchphrase) 
```
```
> Entering new SimpleSequentialChain chain...
RainbowSocks Co.
 "Step into a world of color with RainbowSocks Co.!"

> Finished chain.
 "Step into a world of color with RainbowSocks Co.!"
```

Overall, we thus have a chain that combines langchain and LMQL components, and can be used as a single unit.

::: info Asynchronous Use
You may encounter problems because of the mismatch of LangChain's synchronous APIs with LMQL's `async`-first design.

To avoid problems with this, you can install the [`nest_asyncio`](https://pypi.org/project/nest-asyncio/) package and call `nest_asyncio.apply()` to enable nested event loops. LMQL will then handle event loop nesting and sync-to-async conversion for you.
:::

