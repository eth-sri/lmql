metadata:release: 2023-05-03 17:00:00 +0000
metadata:authors: team

# LMQL v0.0.6.1

We released LMQL v0.0.6.1, which contains several bug fixes and improvements. The most notable changes are:

* **Cache Layer Bug Fixes** This release contains several fixes and improvements to the recently introduced cache layer.

* **Stopping Phrases** Stopping phrases specified via `STOPS_BEFORE` are now passed to the OpenAI API as `"stop"` parameter, decreasing the number of tokens used for the request. If you want to disable this (e.g. to allow speculative execution), you can specify the new decoder parameter `openai_nonstop=True`.

* **Asynchronous Output Writers** All output writers have been refactored to use asynchronous I/O. This should simplify integration with other asynchronous frameworks, e.g. for HTTP or Websocket APIs. We also added a new chapter on [Output Streaming](https://docs.lmql.ai/en/latest/python/output.html) to the documentation.

* **Output Writers for HTTP endpoints, WebSockets and Server-Sent Events** Based on the updated output writer interface, we added three new output writers for serving LMQL queries as HTTP endpoints, WebSockets and via Server-Sent Events (SSE). To learn more, check their relatively simple implementations in the new [lmql.output](https://github.com/eth-sri/lmql/tree/main/src/lmql/output) module. We will also provide more documentation on how to use them, e.g. with `aiohttp` in the future.