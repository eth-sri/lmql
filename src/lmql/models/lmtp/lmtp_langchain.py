"""
Langchain interface to LMTP models.
"""
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import logging

import json
import asyncio
from weakref import WeakValueDictionary
import aiohttp

from langchain.llms.base import LLM
from langchain.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain.llms.utils import enforce_stop_tokens
from langchain.schema import LLMResult

import lmql
from lmql.runtime.tokenizer import LMQLTokenizer
from lmql.runtime.loop import run_in_loop

if TYPE_CHECKING:
    from tenacity import RetryCallState


DEFAULT_ENDPOINT = "localhost:8080"

LOGGER = logging.getLogger(__name__)


class LangchainLMTPStreamError(Exception):
    """
    Raised when the LMTP server returns an error.
    """


class LMTPWebSocketClient:
    """
    Simple 'websockets' based client for LMTP.
    """

    __slots__ = ("sock", "stream_id", "model_identifier", "queues", "handler")

    def __init__(
        self, model_identifier, sock: aiohttp.ClientWebSocketResponse
    ):
        self.sock = sock
        self.stream_id = 0
        self.model_identifier = model_identifier

        self.queues: WeakValueDictionary[
            int, asyncio.Queue
        ] = WeakValueDictionary()
        self.handler = None

    async def generate(self, prompt, **kwargs):
        """
        Given a token ID prompt, generate a
        stream of tokens from the LMTP server.
        """
        self.stream_id += 1
        payload = {
            **kwargs,
            "model": self.model_identifier,
            "prompt": prompt,
            "stream_id": self.stream_id,
        }
        await self.sock.send_str(f"GENERATE {json.dumps(payload)}")

        async for token in self.stream_iterator(self.stream_id):
            yield token

    async def stream_iterator(self, stream_id: int):
        """
        Streams tokens from the read queue.
        """
        queue: asyncio.Queue = asyncio.Queue()
        self.queues[stream_id] = queue

        while True:
            item = await queue.get()

            if item.get("error") is not None:
                raise LangchainLMTPStreamError(item["error"])

            if item is None:
                break
            if item.get("finish_reason") is not None:
                yield item
                break
            yield item

    def connect(self):
        """
        Connect to the LMTP server.
        """

        async def msg_handler():
            async for msg in self.sock:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self.handle(msg)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

        self.handler = asyncio.create_task(msg_handler())

    def handle(self, msg):
        """
        Handle a message from the LMTP server.
        """
        cmd, args = msg.data.split(" ", 1)
        if cmd == "TOKEN":
            payload = json.loads(args)

            for data in payload:
                stream_id = data["stream_id"]
                consumer = self.queues.get(stream_id, None)
                if consumer is not None:
                    consumer.put_nowait(data)
        else:
            LOGGER.warning("Unknown command: %s", cmd)


class _AsyncWrapperForSyncCallbackManagerForRun(AsyncCallbackManagerForLLMRun):
    def __init__(self, callback_manager: "CallbackManagerForLLMRun"):
        super().__init__(
            run_id=callback_manager.run_id,
            handlers=callback_manager.handlers,
            inheritable_handlers=callback_manager.inheritable_handlers,
            parent_run_id=callback_manager.parent_run_id,
            tags=callback_manager.tags,
            inheritable_tags=callback_manager.inheritable_tags,
            metadata=callback_manager.metadata,
            inheritable_metadata=callback_manager.inheritable_metadata,
        )
        self.callback_manager = callback_manager

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        return self.callback_manager.on_llm_new_token(token, **kwargs)

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        return self.callback_manager.on_llm_end(response, **kwargs)

    async def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        return self.callback_manager.on_llm_error(error, **kwargs)

    async def on_text(self, text: str, **kwargs: Any) -> None:
        return self.callback_manager.on_text(text, **kwargs)

    async def on_retry(
        self, retry_state: "RetryCallState", **kwargs: Any
    ) -> None:
        return self.callback_manager.on_retry(retry_state, **kwargs)


class LMTP(LLM):
    """LMTP LLM models.

    This should work with any server compatible with
     the LMQL LMTP protocol. The reference implementation
     of this is `lmql-serve` in the ``lmql`` python package.

    As LMTP requires tokenization be performed clientside,
     this implementation uses the ``lmql`` tokenizer loader
     to support the same class of models as the ``lmql``
     server.

    You must have ``lmql`` installed to use this.

    Example:
        .. code-block:: python

            from langchain_lmtp import LMTP

            llm = LMTP(
                model="gpt2",
                temperature=1.7,
                max_length=10,
                # endpoint="localhost:8080", # default
            )
    """

    model: str
    """The model identifier to send to the LMTP server."""

    endpoint: str = DEFAULT_ENDPOINT
    """The endpoint to use for the LMTP server."""

    max_length: Optional[int] = None
    """Number of tokens to generate

    minimum: 1
    maximum: model-specific
    """

    temperature: Optional[float] = None
    """Temperature to use for generation.

    If None, uses argmax sampling.
    minimum: 0.0
    """

    tokenizer: Optional[LMQLTokenizer] = None
    """The tokenizer to use for this model. You should not need to set this."""

    client: Optional[LMTPWebSocketClient] = None
    """The client to use for this model. You should not need to set this."""

    @property
    def _llm_type(self) -> str:
        return "lmql_lmtp"

    def _get_param(self, _key: str, _kwarg_dict: Dict[str, Any]) -> Any:
        """Get a parameter for the LLM sampling process."""
        return getattr(self, _key, None) or _kwarg_dict.get(_key)

    def _get_params(self, _kwarg_dict: Dict[str, Any]) -> Any:
        """Get parameters for the LLM sampling process."""
        result = {}
        for key in ("max_length", "temperature"):
            value = self._get_param(key, _kwarg_dict)
            if value is None:
                continue
            if key == "max_length":
                key = "max_tokens"
            result[key] = value
        return result

    def _get_tokenizer(self) -> LMQLTokenizer:
        if self.tokenizer is None:
            self.tokenizer = lmql.model(self.model).get_tokenizer()
        return self.tokenizer

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional["CallbackManagerForLLMRun"] = None,
        **kwargs,
    ) -> str:
        """Call out to LMQL

        Args:
            prompt: The prompt to pass into the model.
            stop: A list of strings to stop generation when encountered.

        Returns:
            The string generated by the model.

        Example:
            .. code-block:: python
                response = llm("Once upon a time, ")
        """
        loop = None
        try:
            loop = asyncio.get_running_loop()  # Throws if not in async context
        except RuntimeError as err:
            if "loop" in str(err):
                pass
            else:
                raise
        if loop is not None:
            raise RuntimeError(
                "You may not use the synchronous interface to LMTP "
                "from within an async context. Please await the "
                "async interface instead.\n"
                "e.g. in an iPython Notebook, change `llm.predict(...)` to "
                "`await llm.apredict(...)`"
            )

        coro = self._acall(
            prompt,
            stop,
            _AsyncWrapperForSyncCallbackManagerForRun(run_manager)
            if run_manager is not None
            else None,
            **kwargs,
        )
        return asyncio.run(coro)

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional["AsyncCallbackManagerForLLMRun"] = None,
        **kwargs,
    ) -> str:
        """Asynchronous Call out to LMQL

        Args:
            prompt: The prompt to pass into the model.
            stop: A list of strings to stop generation when encountered.

        Returns:
            The string generated by the model.
        """
        prompt_len = len(prompt)
        last_seen_len = prompt_len
        tokenizer: LMQLTokenizer = self._get_tokenizer()
        input_ids = list(tokenizer(prompt)["input_ids"])

        params = self._get_params(kwargs)

        decoded = None

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect("ws://" + self.endpoint) as sock:
                client = LMTPWebSocketClient(self.model, sock)
                client.connect()

                ids = [
                    *input_ids,
                ]
                async for token in client.generate(input_ids, **params):
                    ids.append(token["token"])

                    if run_manager is not None or stop:
                        decoded = tokenizer.decode(ids)
                        if run_manager is not None:
                            await run_manager.on_llm_new_token(
                                decoded[last_seen_len:]
                            )
                            last_seen_len = len(decoded)
                        if stop:
                            new = decoded[last_seen_len:]
                            for stop_token in stop:
                                if stop_token in new:
                                    break

        result = (decoded or tokenizer.decode(ids))[prompt_len:]

        if stop is not None:
            result = enforce_stop_tokens(result, stop)

        return result
