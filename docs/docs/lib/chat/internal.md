---
order: 3
---
# Internal Reasoning

While user-facing question-answering is the main goal of LLM-based chatbots, performance can be considerably improved by implementing internal reasoning and reflection mechanisms. In this chapter, we will discuss the implementation of such mechanisms in LMQL Chat.

<figure align="center" style="width: 100%; margin: auto;" alt="Screenshot of the model dropdown in the playground">
    <img style="min-height: 100pt" src="https://github.com/eth-sri/lmql/assets/17903049/cb609b5c-8984-414a-a3b6-b3fa6f8ab6bb" alt="Screenshot of the model dropdown in the playground"/>
    <figcaption>A chatbot that relies on internal reasoning.</figcaption>
</figure>

Building on the simple chat application implemented in [](./overview.md), we extend the chat loop as follows:

```{lmql}

name::chat-with-reflection
from lmql.lib.chat import message

argmax 
    "{:system} You are a marketing chatbot for the language \
    model query language (LMQL). Before answering provide \
    some internal reasoning to reflect. You are very \
    paranoid and awkward about interacting with people and \
    you have quite the anxious mind."
    
    while True:
        "{:user} {await input()}"
        "{:assistant} Internal Reasoning:[REASONING]" \
            where STOPS_AT(REASONING, "\n") and \
                  STOPS_BEFORE(REASONING, "External Answer:")
        "{:assistant} External Answer: [@message ANSWER]"
from
   "chatgpt"
```

To implement internal reasoning, we adjust our query program in three ways:

1. We adapt the `{:system}` prompt to include additional instructions that make sure the underlying LLM is instructed to produce internal reasoning output.

2. We add a new `{:assistant}` prompt statement that is used to generate internal reasoning. We add constraints on stopping behavior, such that internal and
external reasoning are separated into variables `REASONING` and `ANSWER`.

3. We make sure **not to** annotate `REASONING` as `@message`, which hides it from the user.

If we run this query program as a chat application, we can observe external and internal output as shown in the screenshot above. As specified by the system prompt,
the chabot now indeed exhibits anxious and slighlty paranoid internal reasoning.

