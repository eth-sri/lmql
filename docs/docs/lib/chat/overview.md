---
order: 0
---
# Your First Chatbot

This chapter will walk you through the process of implementing a simple LMQL chat applications. For this, we will implement a chatbot that responds to user messages while also considering a system prompt, that you will provide during development. 

## 1. The Core Chat Loop

A chatbot is an interactive applications that continously responds to user input. To implement this in LMQL, we can simply use a `while` loop that repeatedly calls the `input()` function to wait for and process user input. 

```{lmql}

name::simple-chat
from lmql.lib.chat import message

argmax 
    while True:
        "{:user} {await input()}"
        "{:assistant} [@message ANSWER]"
from
   "chatgpt"
```

> **Note:** You can run this query for yourself in the [LMQL playground](../../index.md). When executed, the playground will provide a simple chat interface in the model output panel.

**Tags** As part of the prompt statements in our program, we use designated `{:user}` and `{:assistant}` tags, to annotate our prompt in a way that allows the model to distinguish between user and assistant messages. 

**Input** Note also, that in LMQL you have to use `await input()` instead of the traditional Python `input()` function, to make sure that the program does not block while waiting for user input.

**@message** To differentiate between internal output and user-facing chat message output, you can use the `@message` decorator function. This way, only the output of the decorated variables will be displayed to the user, whereas intermediate reasoning is kept internal. To learn more about chat serving, make sure to also read the chapter on [Chat Serving](./serving.md).

With respect to model choice, we use the `chatgpt` model here. Nonetheless, based on LMQL's broad support for different [inference backends](../../models/index.md), the model can be easily replaced with any other supported model. For ChatGPT, tags like `{:user}` directly translate to [OpenAI roles](https://platform.openai.com/docs/guides/gpt/chat-completions-api). For other models, LMQL inserts equivalent raw text annotations, e.g. `((user)):`.

## 2. Adding a System Prompt

While the above program already works, it is not very personalized. To make the chatbot more engaging, we can add a *system prompt* that instructs the model to respond in a specific way. The system prompt is an additional instruction that we include at the beginning of our program and will not be directly visible to the user.

To add a system prompt, we can simply include an additional annotated `{:system}` prompt statement:

```{lmql}

name::chat-with-system
from lmql.lib.chat import message

argmax 
    "{:system} You are a marketing chatbot for the\
     language model query language (LMQL)."
    while True:
        "{:user} {await input()}"
        "{:assistant} [ANSWER]"
from
   "chatgpt"
```

To resulting chat application will now respond in a more personalized way, as it will consider the system prompt before responding to user input. In this case, we instruct it to respond as LMQL marketing agent. 

## 3. Serving the Chatbot

Lastly, to move beyond the playground, we can use the `lmql chat` command to serve our chatbot as a local web application. To do so, we just save the above program as `chat.lmql` and run the following command:

```bash
lmql chat chat.lmql
```

Once the server is running, you can access the chatbot at the provided local URL. 

<figure align="center" style="width: 100%; margin: auto;" alt="Screenshot of the model dropdown in the playground">
    <img style="min-height: 100pt" src="https://github.com/eth-sri/lmql/assets/17903049/334e9ab4-aab8-448d-9dc0-c53be8351e27" alt="Screenshot of the model dropdown in the playground"/>
    <figcaption>A simple chatbot using the LMQL Chat UI.</figcaption>
</figure>

In this interface, you can interact with your chatbot by typing into the input field at the bottom of the screen. The chatbot will then respond to your input, while also considering the system prompt that you provide in your program. On the right, you can inspect the full internal prompt of your program, including the generated prompt statements and the model output. This allows you at all times, to understand what exact input the model received and how it responded to it.

## Learn More

To learn more, return to the [Chat overview page](../chat.md) and pick one of the provided topics.