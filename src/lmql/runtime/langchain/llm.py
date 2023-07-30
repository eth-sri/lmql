from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

import functools

from langchain.llms.base import LLM

import lmql
from lmql.runtime.output_writer import BaseOutputWriter

if TYPE_CHECKING:
    from lmql.models.model import LMQLModel
    from langchain.callbacks.manager import (
        AsyncCallbackManagerForLLMRun,
        CallbackManagerForLLMRun,
    )

DEFAULT_ENDPOINT = "localhost:8080"


class _TextChunkCallbackWriter(BaseOutputWriter):
    """Writes new tokens to a given callback."""

    __slots__ = ("callback", "last_length")

    def __init__(
        self,
        callback: Callable[[str], Any],
        initial_length: int = 0,
    ) -> None:
        """Initialize the callback writer."""
        super().__init__(allows_input=False)
        self.callback = callback
        self.last_length = initial_length

    async def add_interpreter_head_state(
        self,
        variable,
        head,
        prompt: str,
        where,
        trace,
        is_valid,
        is_final,
        mask,
        num_tokens,
        program_variables,
    ) -> None:
        last_length = self.last_length
        self.last_length = len(prompt)
        self.callback(prompt[last_length:])


class LMQL(LLM):
    """LMQL LLM models.

    This piggybacks on LMQL to use any server compatible with
     the LMTP protocol, so you should have the ``lmql``
     python package installed.

    Example:
        .. code-block:: python

            from langchain_lmtp import LMTP

            llm = LMTP(model_id="lmtp://localhost:8000/1")
    """

    model: Union[str, "LMQLModel"]
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

    verbose: bool = False
    """Whether to print prepared querystrings before use."""

    @property
    def _llm_type(self) -> str:
        return "lmql_lmtp"

    def _get_param(self, _key: str, _kwarg_dict: Dict[str, Any]) -> Any:
        """Get a parameter for the LLM sampling process."""
        return getattr(self, _key, None) or _kwarg_dict.get(_key)

    def _prepare_querystring(
        self,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        max_length = self._get_param("max_length", kwargs)

        constraint_list = []
        if max_length is not None and max_length > 0:
            constraint_list.append(f"len(TOKENS(COMPLETION)) < {max_length+1}")
        if stop is not None:
            stop_constraints = " or ".join(
                f"STOPS_BEFORE(COMPLETION, '{stopword}')" for stopword in stop
            )
            constraint_list.append(f"({stop_constraints})")
        constraints = (
            " and ".join(constraint_list) if constraint_list else None
        )

        temperature = self._get_param("temperature", kwargs)

        if temperature is not None:
            sampler_kwargs = {"temperature": temperature}
            # Whoops! Turns out not a valid decoder arg
            # top_k = self._get_param("top_k", kwargs)
            # if top_k is not None and top_k > 0:
            #     sampler_kwargs["top_k"] = top_k

            if sampler_kwargs:
                sampler_kwargs_formatted = ", ".join(
                    (f"{key}={value}" for key, value in sampler_kwargs.items())
                )
                sampler_formatted = f"sample({sampler_kwargs_formatted})"
        else:
            sampler_formatted = "argmax"

        result = f'{sampler_formatted}\n    "{{prompt}}[COMPLETION]"\n'

        if constraints:
            result += f"where\n    {repr(str(constraints))[1:-1]}"

        if self.verbose:
            print(f"LMQL LLM Query String:\n{result}")

        return result

    def _prepare_query(
        self,
        is_async: bool,
        stop: Optional[List[str]] = None,
        run_manager: Optional[
            Union["AsyncCallbackManagerForLLMRun", "CallbackManagerForLLMRun"]
        ] = None,
        **kwargs: Any,
    ) -> lmql.LMQLQueryFunction:
        """Prepare a query function for the LLM sampling process."""
        querystr: str = self._prepare_querystring(stop=stop, **kwargs)

        output_writer = lmql.headless
        if run_manager:
            text_chunk_callback = functools.partial(
                run_manager.on_llm_new_token, verbose=self.verbose
            )
            output_writer = _TextChunkCallbackWriter(
                text_chunk_callback, initial_length=0
            )

        return lmql.query(
            querystr,
            is_async=is_async,
            output_writer=output_writer,
        )

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

        model = (
            lmql.model(self.model, endpoint=self.endpoint)
            if isinstance(self.model, str)
            else self.model
        )

        query = self._prepare_query(
            is_async=False,
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )

        result: List[lmql.LMQLResult] = query(model=model, prompt=prompt)

        prompt_len: int = len(prompt)

        return result[0].prompt[prompt_len:]

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

        model = (
            lmql.model(self.model, endpoint=self.endpoint)
            if isinstance(self.model, str)
            else self.model
        )

        query = self._prepare_query(
            is_async=True,
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )

        result: List[lmql.LMQLResult] = await query(model=model, prompt=prompt)

        prompt_len: int = len(prompt)

        return result[0].prompt[prompt_len:]
