# Serving

Next to building your chat application, serving it is the next step before it can be used by others. To facilitate this and to offer a starting point for your custom implementation, LMQL includes a simple server implementation and corresponding client web UI, that communicate via the [`websocket` protocol](https://tools.ietf.org/html/rfc6455).

To access and use this implementation we offer two routes: (1) Use the `lmql chat` command directly with your `.lmql` file, or (2) use the `lmql.chat` function from your own code.

## Using the `lmql chat` command

To locally serve an LMQL chat endpoint and user interface, simply run the following command:

```bash
lmql chat <path-to-lmql-file>.lmql
```

This will serve a web interface on `http://localhost:8089`, and automatically open it in your default browser. You can now start chatting with your custom LMQL chat application. The internal trace on the right-hand side always displays the complete current prompt, reflecting the current state of your chat application.

Note that changing the `.lmql` file will **not** automatically reload the server, so you will have to restart the server manually to see the changes.

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

## Using the `lmql.chat` function

Alternatively, to launch the LMQL chat server from your own code, you can use the `lmql.chat` function. This function takes the path of the query file as its only argument, and returns a chat server object, that can be launched using `run()`:

```python
import lmql

lmql.chat('path/to/my-query.lmql').run()
```

## More Advanced Usage

For more advanced serving scenarios, e.g. when integrating Chat into your own web applications, please refer to the very minimal implementation of the `lmql.chat` in [`src/lmql/ui/chat/__init__.py`](https://github.com/eth-sri/lmql/blob/main/src/lmql/ui/chat/__init__.py). This implementation is very minimal and can be easily adapted to your own needs and infrastructure. The corresponding web UI is implemented in [`src/lmql/ui/chat/assets/`](https://github.com/eth-sri/lmql/blob/main/src/lmql/ui/chat/assets/) and offers a good starting point for your own implementation and UI adaptations on the client side.

For other forms of output streaming e.g. via HTTP or SSE, see also the chapter on [Output Streaming](../output.ipynb)