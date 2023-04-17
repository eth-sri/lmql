"""
Serves a llama.cpp model as LMQL inference API.
"""

from queue import Empty
import multiprocessing
from typing import Optional, Tuple
import atexit
import argparse
import time
from llama_cpp.llama import Llama
import inspect
from lmql.model.serve_types import (
    TokenizerProcessor,
    ModelProcessor,
    InferenceServerState,
)


class LlamaCPPTokenizerProcessor(TokenizerProcessor):
    def __init__(self, state: InferenceServerState, processor: "ModelProcessor"):
        super().__init__(state)
        self.model = processor

    def tokenize(self, tokenizer, sample_id, client_id, item):
        text = item["text"]

        if text == "<EOS>":
            input_ids = [tokenizer.token_eos()]
        elif text == "<BOS>":
            input_ids = [tokenizer.token_bos()]
        else:
            input_ids = tokenizer.tokenize(b" " + text.encode("utf-8"))

        self.state.all_results_queue.put(
            {"sample_id": sample_id, "client_id": client_id, "input_ids": input_ids}
        )

    def detokenize(self, tokenizer, sample_id, client_id, item):
        input_ids = item["input_ids"]

        text = tokenizer.detokenize(input_ids).decode("utf-8")
        self.state.all_results_queue.put(
            {"sample_id": sample_id, "client_id": client_id, "text": text}
        )

    def run(self):
        # load tokenizer
        tokenizer = self.model
        print("Tokenizer {} ready!".format(self.model_identifier))

        while not self.state.exit:
            item = self.queue.get()
            if item is None:
                time.sleep(0.1)
                continue

            sample_id = item["sample_id"]
            client_id = item["client_id"]
            action = item["action"]

            if action == "tokenize":
                self.tokenize(tokenizer, sample_id, client_id, item)
            elif action == "detokenize":
                self.detokenize(tokenizer, sample_id, client_id, item)
            else:
                print("error: unknown TokenizerProcessor action {}".format(action))

        print("Tokenizer shut down.")

    def run_in_parallel(self):
        atexit.register(self.shutdown)

        p = multiprocessing.Process(target=self.run)
        p.start()
        return p


class LlamaCPPModelProcessor(ModelProcessor):
    def __init__(
        self,
        state: InferenceServerState,
        cuda: bool = False,
        cache: Optional[str] = None,
        llama_kwargs: Optional[dict] = None,
    ):
        super().__init__(state, cuda, cache)
        assert llama_kwargs is not None
        self.llama_kwargs = llama_kwargs

    def run(self):
        # load model
        print("Loading {} (CPU)".format(self.model_identifier))
        self.model = Llama(**{**self.llama_kwargs, "logits_all": True})

        print("Ready!".format(self.model_identifier))

        while not self.state.exit:
            self.print_stats()
            # wait for self.queue to have an item
            try:
                item = self.queue.get(timeout=1.0)
            except Empty:
                continue
            except KeyboardInterrupt:
                break

            if item is None:
                time.sleep(0.1)
                continue

            self.request_count += 1

            sample_id = item["sample_id"]
            client_id = item["client_id"]
            input_ids = item["input_ids"]

            if self.cache is not None:
                key = str(input_ids)
                if key in self.cache:
                    self.requests_cached += 1
                    self.state.all_results_queue.put(
                        {
                            "client_id": client_id,
                            "sample_id": sample_id,
                            "next_token_logits": self.cache[key],
                        }
                    )
                    continue
            self.model.reset()
            res = self.model.eval(input_ids[0])

            next_token_logits = self.model.all_logits[-1]

            if self.cache is not None:
                key = str(input_ids.tolist())
                self.cache[key] = next_token_logits

            self.state.all_results_queue.put(
                {
                    "client_id": client_id,
                    "sample_id": sample_id,
                    "next_token_logits": [next_token_logits],
                }
            )

        print("Processor shut down")

    def run_in_parallel(self):
        atexit.register(self.shutdown)

        p = multiprocessing.Process(target=self.run)
        p.start()
        return p


base_llama_kwargs = {}


def get_serve(
    state: InferenceServerState, args: argparse.Namespace
) -> Tuple[ModelProcessor, TokenizerProcessor]:
    # run model in separate process
    llama_kwargs = {kwarg: getattr(args, kwarg) for kwarg in base_llama_kwargs.keys()}
    processor = LlamaCPPModelProcessor(
        state, cuda=False, cache=args.cache, llama_kwargs=llama_kwargs
    )
    processor.run_in_parallel()

    # run tokenizers in separate process
    tokenizer_processor = LlamaCPPTokenizerProcessor(state, processor=processor)
    tokenizer_processor.run_in_parallel()
    return processor, tokenizer_processor


def add_parser(base_parser):
    sig = inspect.signature(Llama.__init__)
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        base_llama_kwargs[name] = None
        _type = param.annotation
        if hasattr(_type, "__args__"):
            _type = _type.__args__[0]
        if param.default == inspect.Parameter.empty:
            base_parser.add_argument(
                f"--{name}", default=_type(), type=_type, help="required for llama.cpp"
            )
        else:
            base_parser.add_argument(
                f"--{name}",
                default=param.default,
                type=_type,
                help="optional for llama.cpp",
            )
