# Chat

<!-- ![A simple chatbot using the LMQL chat UI)](https://github.com/eth-sri/lmql/assets/17903049/334e9ab4-aab8-448d-9dc0-c53be8351e27) -->

Building chat applications is one of the most common use cases for LLMs. This is why LMQL provides designated library support for it.  This chapter will walk you through the basics of building a chatbot with LMQL including the core loop, output streaming, serving and defending against prompt injections.

```{figure} https://github.com/eth-sri/lmql/assets/17903049/3f24b964-b9b6-4c50-acaa-b38e54554506
:name: lmql-chat
:alt: An overview of the LMQL Chat library.
:align: center

An overview of the LMQL Chat library.
```

To get started choose one of the following topics:

::::{grid} 2
:::{grid-item-card} 👶🏽 Your first LMQL Chatbot
:link: ./chat/overview.md
Learn the basics of LMQL Chat by building a simple chatbot.
:::
:::{grid-item-card} 🏄‍♀️ Serving your Chatbot
:link: ./chat/serving.md
Learn how to serve your chatbot via a WebSockets API.
:::
<!-- :::{grid-item-card} 🛠️ Integrating Tools
:link: ./chat/tools.md
Expose tools to your chatbot, to enable more complex interactions.
::: -->
:::{grid-item-card} 🛡️ Defend against Prompt Injections
:link: ./chat/defend.md
Perform input sanitization to defend against prompt injection attacks.
:::
::::

```{toctree}
:hidden:

chat/overview
chat/serving
<!-- chat/tools -->
chat/defend
```