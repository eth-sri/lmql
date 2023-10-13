---
order: 1
---
# Serving

After building your chat application, serving it is the next step before it can be used by others. To facilitate this and to offer a starting point for your custom implementation, LMQL includes a simple server implementation and corresponding client web UI, that communicate via the [`websocket` protocol](https://tools.ietf.org/html/rfc6455).

To access and use this implementation we offer two routes: (1) Use the `lmql chat` command directly with your `.lmql` file, or (2) use the `lmql.chat.chatserver` from your own code.

## Using the `lmql chat` command

To locally serve an LMQL chat endpoint and user interface, simply run the following command:

```bash
lmql chat <path-to-lmql-file>.lmql
```

This will serve a web interface on `http://localhost:8089`, and automatically open it in your default browser. You can now start chatting with your custom LMQL chat application. The internal trace on the right-hand side (shown below), always displays the complete (conversational) prompt, reflecting the current state of your chat application.

Note that changing the `.lmql` file will **not** automatically reload the server, so you will have to restart the server manually to see the changes.

<figure align="center" style="width: 100%; margin: auto;" alt="A simple chatbot using the LMQL Chat UI.">
    <img style="min-height: 100pt" src="https://github.com/eth-sri/lmql/assets/17903049/334e9ab4-aab8-448d-9dc0-c53be8351e27" alt="A simple chatbot using the LMQL Chat UI."/>
    <br/><figcaption>A simple chatbot launched via <code>lmql chat</code>.</figcaption>
</figure>

## Using `chatserver` 

Alternatively, to launch the LMQL chat server from your own code, you can use `lmql.lib.chat.chatserver`. This c;ass takes the path of the query file or a query function as argument, and returns a chat server object, that can be launched using `run()`:

```python
from lmql.lib.chat import chatserver

chatserver('path/to/my-query.lmql').run()
```

Note that when passing a query function directly, you have to always provide a `async def` function, which enables concurrent client serving.

## `@message` Streaming

Chat relies on a [decorator-based](../../language/decorators.md) output streaming. More specifically, only model output variables that are annotated as `@message` are streamed and shown to the user in the chat interface. This allows for a clean separation of model output and chat output, and eneables hidden/internal reasoning. 

To use `@message` with your [custom output writer](../output.html), make sure to inherit from `lmql.lib.chat`'s `ChatMessageOutputWriter`, which offers additional methods for specifically handling and streaming `@message` variables.

## More Advanced Usage

For more advanced serving scenarios, e.g. when integrating Chat into your own web applications, please refer to the very minimal implementation of `chatserver` in [`src/lmql/ui/chat/__init__.py`](https://github.com/eth-sri/lmql/blob/main/src/lmql/ui/chat/__init__.py). This implementation is very minimal and can be easily adapted to your own needs and infrastructure. The corresponding web UI is implemented in [`src/lmql/ui/chat/assets/`](https://github.com/eth-sri/lmql/blob/main/src/lmql/ui/chat/assets/) and offers a good starting point for your own implementation and UI adaptations on the client side.

For other forms of output streaming e.g. via HTTP or SSE, see also the chapter on [Output Streaming](../output.html)

**Disclaimer**: The LMQL chat server is a simple code template that does not include any security features, authentication or cost control. It is intended for local development and testing only, and should not be used as-is in production environments. Before deploying your own chat application, make sure to implement the necessary security measures, cost control and authentication mechanisms.