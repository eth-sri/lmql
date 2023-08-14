# Your First Chatbot

This chapter will walk you through the process of implementing a simple LMQL chat applications. For this, we will implement a chatbot that responds to user messages while also considering a system prompt, that you will provide during development. 

## 1. The Core Chat Loop

A chatbot is an interactive applications that continously responds to user input. To implement this in LMQL, we can simply use a `while` loop that repeatedly calls the `input()` function to wait for and process user input. 

```{lmql}

name::simple-chat
argmax 
    while True:
        "{:user} {await input()}"
        "{:assistant} [ANSWER]"
from
   "chatgpt"
```

> **Note:** You can already run this query for yourself, by just pasting it into the [LMQL playground](../../quickstart.md). When executed, the playground will provide a simple chat interface as part of the model output panel.

As part of the prompt statements in our program, we use designated `{:user}` and `{:assistant}` tags, to annotate our prompt in a way that the model can distinguish between user and assistant messages.

Note also, that in LMQL you have to use `await input()` instead of the traditional Python `input()` function, to make sure that the program does not block while waiting for user input.

With respect to model choice, we use the `chatgpt` model here. Nonetheless, based on LMQL's broad support for different [inference backends](../../language/models.rst), the model can be easily replaced with any other supported model.

## 2. Adding a System Prompt

While the above program already works, it is not very personalized, as it does not consider any system prompt. To add a system prompt, we can simply include an additional annotated `{:system}` prompt statement:

```{lmql}

name::chat-with-system
argmax 
    "{:system} You are a marketing chatbot for the\
     language model query language (LMQL)."
    while True:
        "{:user} {await input()}"
        "{:assistant} [ANSWER]"
from
   "chatgpt"
```

## 3. Serving the Chatbot

Last, to move beyond the LMQL playground, we can use the `lmql chat` command to serve our chatbot as a local web application. To do so, we just save the above program as `chat.lmql` and run the following command:

```{bash}
lmql chat chat.lmql
```

Once the server is running, you can access the chatbot at the provided local URL. 

```{toctree}
:hidden:

./chat/overview
```

```{figure} https://github.com/eth-sri/lmql/assets/17903049/334e9ab4-aab8-448d-9dc0-c53be8351e27
:name: lmql-chat
:alt: A simple chatbot using the LMQL chat UI
:align: center

A simple chatbot using the LMQL Chat UI.
```

In this interface, you can interact with your chatbot by typing into the input field at the bottom of the screen. The chatbot will then respond to your input, while also considering the system prompt that you provided in your LMQL program. On the right, you can inspect the full internal trace of your program, including the generated prompt statements and the model output. This allows you at all times, to understand what exact input the model received and how it responded to it.

## Learn More

To learn more, return to the [Chat overview page](../chat.md) and pick one of the provided topics.