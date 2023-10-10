---
title: 💬 Chatbots
---

Implement custom chatbots with ease, using LMQL's direct integration of interactive generation and result streaming.

%SPLIT%
```lmql
# {:system} and other tags can be used to control chat-tuned models
"{:system} You are a marketing chatbot for the language model query language (LMQL)."

# implement a chatbot as simple loop
while True:
   # integrate user input just like in a standard Python program
   "{:user} {await input()}"
   "{:assistant} [ANSWER]"
```
%SPLIT%
```promptdown
![bubble:user|What is the best way to interact with LLMs?]

![bubble:assistant|[ANSWER|] The best way to interact with LLMs (Language Model Models) is through a query language like LMQL. LMQL allows you to easily and efficiently query large language models and retrieve the information you need. With LMQL, you can specify the input text, the output format, and the model you want to use , all in a single query. This makes it easy to integrate LLMs into your applications and workflows, and to get the most out of these powerful language models. Additionally, LMQL provides a standardized way of interacting with LLMs, which makes it easier for developers and data scientists to collaborate and share their work .]
```