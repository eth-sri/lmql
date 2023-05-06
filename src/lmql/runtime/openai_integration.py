import asyncio
import inspect
import os
from collections import namedtuple
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Union

import numpy as np

import lmql.runtime.masks as masks
import lmql.runtime.bopenai as openai
import lmql.runtime.dclib as dc
import lmql.utils.nputil as nputil
from lmql.runtime.dclib.dclib_model import DcModel
from lmql.runtime.dclib.dclib_seq import (DecoderSequence, deepcopy, deepmerge,
                                          detseq, is_deterministic)
from lmql.runtime.stats import Stats
from lmql.runtime.tokenizer import load_tokenizer
from lmql.utils import nputil


def is_allowed(m): 
    """
    Given a logits mask, sets tensor cell value to True iff the corresponding token is allowed according to the mask.
    """
    return np.isclose(m, 0, atol=1e-8)

def openai_complete_create(*args, **kwargs):
    if kwargs.get("chaos", False):
        import random
        if random.random() < 0.5:
            if random.random() < 0.5:
                raise openai.error.ServiceUnavailableError("Chaos monkey error", 500, "Chaos monkey error")
            else:
                raise openai.error.APIError("Chaos monkey error", 500, "Chaos monkey error")

    return openai.Completion.create(*args, **kwargs)

@dataclass
class CompleteTask:
    op: Callable
    result: Any
    continuation_type: str
    logit_mask_or_fixed_id: Optional[Union[np.ndarray, int]] = None

    async def run(self, retries):
        try:
            return CompleteTask(self.op, await self.op(), self.continuation_type, self.logit_mask_or_fixed_id)
        except Exception as e:
            if type(e) is not openai.error.APIError and type(e) is not openai.error.ServiceUnavailableError:
                raise e
            if retries > 0:
                print("OpenAI API error: ", e, ". Retrying...", flush=True)
                print("Retrying operation due to OpenAI API error", e)
                return await self.run(retries - 1)
            else:
                print("Exceeded ", retries, " retries. Giving up.", flush=True)
                raise e

@dataclass
class CompletionResult:
    buffer: openai.response_buffer
    continuation_type: str
    logit_mask_or_fixed_id: Optional[Union[np.ndarray, int]] = None

@dataclass
class CompletionCall:
    mode: str
    logit_mask_or_fixed_id: np.ndarray
    input_ids: np.ndarray
    kwargs: Any
    stopping_phrases: List[str] = None
    
    # true iff inverting the api_mask leads to a smaller mask
    invert: bool = False
    
    @property
    def api_mask(self, invert=None):
        mask = self.logit_mask_or_fixed_id
        assert nputil.is_array(mask), "api_mask(): logit_mask_or_fixed_id must be a LongTensor not a " + str(type(mask))
        
        if self.invert:
            masked = (mask >= 0)
        else:
            masked = (mask < 0)
        mask_value = 100 if self.invert else -100
        return {int(idx): mask_value for idx in np.nonzero(masked)[0]}

    @property
    def continuation_type(self):
        if self.mode == "fixed":
            return None
        # unique cache key identifying the type of this completion
        parameter_values_key_segment = "temp-" + str(self.kwargs["temperature"]) + "-logprobs-" + str(self.kwargs["logprobs"])
        if self.mode == "complete":
            api_mask = self.api_mask
            mask_key_segment = [f"{id}={value}" for id, value in sorted(api_mask.items(), key=lambda x: x[0])]
            mask_key_segment = "-".join(mask_key_segment)
        else:
            mask_key_segment = "*"
        return f"{parameter_values_key_segment}-{mask_key_segment}"

class DclibOpenAiModel(DcModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, truncation_threshold=-120, init_workers=False, **kwargs)

        # if available, store reference to output writer for eager stats reporting
        self.output_writer = None
        if "output_writer" in kwargs:
            self.output_writer = kwargs["output_writer"]
        
        self.model_identifier = "openai/" + self.model.model_identifier

        self.model.chunk_size = kwargs.get("openai_chunksize", 64)
        self.model.nostop = kwargs.get("openai_nonstop", False)
        self.num_billed_tokens = {}
        self.num_requests = 0

        self.stats = Stats("openai")
        openai.AsyncConfiguration.set_tokenizer(self.tokenize)

    def log_billable_tokens(self, n: int):
        pass # openai keeps track of billable tokens vai bopenai
    
    def log_queries(self, n: int):
        pass # openai keeps track of queries via bopenai

    def prepare_completion_call(self, s, mask, **kwargs):
        """
        Computes an API compatible mask from the provided logit mask, as well as the required mode of completion.

        Returns Values:
            - (mask_dict, "*"): Complete with the full vocabulary (no logit_bias necessary)
            - (mask_dict, "complete"): Complete with the provided mask mask_dict, to be passed like this to the OpenAI endpoint.
            - (token_id, "fixed"): Complete with the provided token_id with full probability 1.0 (no API use necessary)

        """
        stopping_phrases = s.data("head").stopping_phrases["text"]

        if mask is None:
            return CompletionCall("*", None, s.input_ids, kwargs, stopping_phrases=stopping_phrases)

        invert = False
        num_allowed = masks.mask_num_allowed(mask)
        assert num_allowed > 0, "DclibOpenAiModel: encountered logits mask with no allowed tokens: mask: {} mask type:{}".format(mask, type(mask))

        if num_allowed == 1:
            # check for <eos> case
            if masks.mask_is_allowed(mask, self.eos_token_id):
                return CompletionCall("fixed", self.eos_token_id, s.input_ids, kwargs, stopping_phrases=stopping_phrases)
            else:
                # otherwise we can treat this as a score call
                return CompletionCall("fixed", masks.mask_get_only_allowed(mask), s.input_ids, kwargs, stopping_phrases=stopping_phrases)
        elif num_allowed < self.tokenizer.model_vocab_size:
            if self.tokenizer.model_vocab_size - num_allowed > num_allowed:
                # if we have to mask more than half of the tokens, we should just invert the masking
                invert = True
        else: # num_allowed == mask.shape[-1] (full vocabulary)
            return CompletionCall("*", None, s.input_ids, kwargs, stopping_phrases=stopping_phrases)

        # num_allowed < mask.shape[-1] and num_allowed > 1 (needs mask)
        return CompletionCall("complete", mask, s.input_ids, kwargs, invert=invert, stopping_phrases=stopping_phrases)

    async def api_score(self, input_ids, offset):
        kwargs = {
            "model": self.model.model_identifier,
            "prompt": input_ids.tolist(),
            "max_tokens": 0,
            "temperature": 0,
            "logprobs": 1,
            "user": "lmql",
            "echo": True
        }

        logprobs = []
        async for data in await openai.Completion.create(**kwargs):
            logprobs += data["logprobs"]["token_logprobs"]
        return np.array(logprobs[offset:], dtype=np.float32)

    async def queue_api_score(self, kwargs):
        # put task in self.score_queue and await result
        loop = asyncio.get_running_loop()
        result_fut = loop.create_future()
        self.score_queue.put_nowait((kwargs,result_fut))
        return await result_fut

    async def _score_next_tokens(self, s, next_tokens, noscore=False):
        if noscore:
            return np.zeros(len(next_tokens), dtype=np.float32)
        return (await self.api_score(np.concatenate([s.input_ids, next_tokens], axis=0), len(s.input_ids)))
    
    async def score(self, sqs: List[DecoderSequence], tokens: List[List[int]], max_batch_size=4, deterministic: Union[bool, List[bool]]=False, stop_phrase=False, needs_rewrite=True, user_data=None, noscore=False, internal=False):
        assert len(sqs) == len(tokens), "Number of sequences and number of tokens to be scored must match, but got {} and {}".format(len(sqs), len(tokens))

        def make_detseq(s, token_score, completion):
            # compose deterministic flags
            if type(deterministic) is bool:
                deterministic_flags = np.concatenate([s.deterministic, np.array([deterministic])])
                next_deterministic = np.array([deterministic] * len(completion[1:]))
            else:
                assert type(deterministic) is list and len(deterministic) == len(completion), "If deterministic is a list, it must have the same length as the number of tokens to be scored, but is {} and {}".format(deterministic, completion)
                deterministic_flags = np.concatenate([s.deterministic, np.array(deterministic[:1])])
                next_deterministic = np.array(deterministic[1:])

            return detseq(ids=np.concatenate([s.input_ids, completion[:1]], axis=0), 
                    next_ids=completion[1:],
                    logprobs=np.concatenate([s.logprobs, token_score[:1]], axis=0),
                    next_logprobs=token_score[1:],
                    deterministic=deterministic_flags,
                    next_deterministic=next_deterministic,
                    predecessor=s,
                    user_data=user_data,
                    stop_phrase=np.concatenate([s.stop_phrase, np.array([stop_phrase])]),
                    needs_rewrite=needs_rewrite,
                    sticky_user_data_keys=s.sticky_user_data_keys,
                    internal=internal
            )
        results = []

        async for (s, tokens, scores) in self.score_tokens(sqs, tokens, max_batch_size=max_batch_size, noscore=noscore):
            results.append(make_detseq(s, scores, tokens))

        return results
    
    async def score_tokens(self, sqs: List[DecoderSequence], tokens: List[List[int]], max_batch_size=None, noscore=False):
        completion = [np.array(cont) for cont in tokens]

        for s, tokens,scores in zip(sqs, completion, await asyncio.gather(*(self._score_next_tokens(s, compl, noscore=noscore) for s, compl in zip(sqs, completion)))):
            yield (s, tokens, scores)

    async def async_complete(self, completion_call: Union[CompletionCall, List[CompletionCall]], **kwargs) -> openai.response_buffer:
        assert type(completion_call) is CompletionCall

        batch_size = 1
        input_ids = completion_call.input_ids.reshape(-1)
        assert input_ids.ndim == 1, f"_complete expects input_ids to be a 1D tensor when only one completion_call is passed, got {input_ids.ndim}D tensor."

        temperature = completion_call.kwargs.get("temperature", 0.0)
        logprobs = completion_call.kwargs.get("logprobs", 5)
        noscore = completion_call.kwargs.get("noscore", False)

        kwargs = {
            "model": self.model.model_identifier,
            "prompt": input_ids.tolist(), # no more batching at this point
            "max_tokens": self.model.chunk_size,
            "temperature": temperature,
            "logprobs": logprobs,
            "user": "lmql",
            "stream": True,
            "echo": True
        }

        mode = completion_call.mode
        
        if mode == "*": # complete without mask
            pass
        elif mode == "complete": # complete with mask
            logit_bias = completion_call.api_mask
            # reduce chunk size, if logit mask seems very sparse
            if len(logit_bias) > 0 and max(logit_bias.values()) == 100 and len(logit_bias) < 10:
                kwargs["max_tokens"] = min(kwargs["max_tokens"], 4)
            kwargs.update({"logit_bias": logit_bias})
        elif mode == "fixed": # complete with fixed token
            fixed_next_token = completion_call.logit_mask_or_fixed_id # special return value case for prepare function
            # TODO revisit this, what kind of probability do we want here (masked or unmasked/scored)
            if fixed_next_token == self.eos_token_id:
                return CompletionResult(openai.response_buffer.singleton(token=fixed_next_token, token_logprob=0), completion_call.continuation_type, completion_call.logit_mask_or_fixed_id)
            else:
                fixed_next_token = nputil.ensure_array(fixed_next_token, dtype=np.int64)
                if noscore: logprob = 0.0
                else: logprob = (await self.api_score(np.concatenate([input_ids, fixed_next_token.reshape(1)], axis=0), len(input_ids)))
                return CompletionResult(openai.response_buffer.singleton(token=fixed_next_token, token_logprob=logprob), completion_call.continuation_type, completion_call.logit_mask_or_fixed_id)
        else:
            assert False, f"Internal openai API dispatcher returned an unknown completion mode {mode}"

        if len(completion_call.stopping_phrases) > 0:
            if len(completion_call.stopping_phrases) > 4:
                # same but blaming it more on OpenAI
                print("warning: the number of stopping phrases that would need to be passed to the OpenAI API is greater than 4. Since the OpenAI API only supports up to 4 stopping phrases, the first 4 stopping phrases will be passed to the API. Other stopping phrases will also be enforced, but may lead to an increase in the number of tokens billed to the user.")
            # skip stopping phrases for more speculative execution
            if not self.model.nostop:
                kwargs.update({"stop": completion_call.stopping_phrases[:4]})

        # TODO: we are now overestimate the number of tokens billed to the user since we are not account for stopping phrases for the sake of streaming
        self.count_billed_tokens(input_ids.size + kwargs.get("max_tokens") * batch_size, self.model_identifier)
        
        if self.model_args.get("chatty_openai", False):
            args = kwargs.copy()
            args["prompt"] = str([await self.detokenize(kwargs["prompt"])])[2:-2]
            print(f"openai complete: {args}")

        return CompletionResult((await openai.async_buffer(await openai.Completion.create(**kwargs), tokenizer=self.tokenize_list))[input_ids.size:], completion_call.continuation_type, completion_call.logit_mask_or_fixed_id)
    
    async def tokenize_list(self, tokens: List[str]):
        if len(tokens) > 0 and type(tokens[0]) is str:
            return [[t[0]] for t in await self.model.tokenize(tokens)]
        return tokens
    
    async def openai_cache_delegate(self, kwargs, tokens, scores):
        print(tokens, scores, self.cache_delegate)

    def count_billed_tokens(self, n, model):
        if model not in self.num_billed_tokens.keys():
            self.num_billed_tokens[model] = 0
        self.num_billed_tokens[model] += n
        self.num_requests += 1

    async def completion_buffer(self, seqs, temperature=1, **kwargs):
        kwargs.update({"temperature": temperature})
        
        async def get_buffer(i, s):
            with self.stats.timer("logit_masks"):
                # print("completion_buffer", s)
                constrained_seqs = np.array([s.is_query_constrained], dtype=np.bool_)
                logits_mask_result = await self.compute_logits_mask(s.input_ids.reshape(1, -1), [s.user_data], constrained_seqs, [s], **kwargs)
                logits_mask = logits_mask_result.logits_mask[0]

            # update user data with new information obtained when computing logits masks
            if s.user_data is None:
                s.user_data = {}
            s.user_data = deepmerge(deepcopy(s.user_data), logits_mask_result.user_data[0])
            s.user_data["set_by"] = "where"

            completion_call = self.prepare_completion_call(s, logits_mask, **kwargs)

            # if no masking is required, we can use cached continuations if available
            if s.data("openai-continuations") is not None:
                continuations: CompletionResult = s.data("openai-continuations")
                continuation_type = completion_call.continuation_type

                if continuation_type in continuations:
                    continuation = continuations[continuation_type]
                    if await continuation.buffer.empty():
                        # remove continuation (it's empty)
                        del s.data("openai-continuations")[continuation_type]
                    else:
                        # use continuation instead of issuing a new API call
                        return continuation

            # handle deterministic sequences
            if is_deterministic(s) and len(s.next_ids) > 0:
                return CompletionResult(
                    openai.response_buffer.singleton(token=s.next_ids[0], token_logprob=s.next_logprobs[0]),
                    None,
                    None,
                )

            completion_result = await self.async_complete(completion_call)
            # eagerly expand and cache full completion if a cache_delegate is available
            if self.cache_delegate is not None:
                await self.expand_and_cache(s, completion_result, "top-1", logprobs=kwargs.get("logprobs", 1))
            
            assert not await completion_result.buffer.empty(), "Completion result is empty on arrival"
            return completion_result

        return await asyncio.gather(*[get_buffer(i, s) for i, s in enumerate(seqs)])

    async def expand_and_cache(self, s: DecoderSequence, completion_result: CompletionResult, edge_type, logprobs=1):
        async def token_stream():
            nonlocal edge_type, s, completion_result
            response_buffer = completion_result.buffer
            
            try:
                tokens = []
                scores = []

                while True:
                    try:
                        if await response_buffer.empty():
                            break

                        res = await response_buffer.get(0)
                        tokens = nputil.ensure_iterable(res["logprobs"]["tokens"])
                        scores = res["logprobs"]["token_logprobs"]

                        topprobs = res["logprobs"]["top_logprobs"]
                        if topprobs is not None and logprobs > 1:
                            topk_tokens = list(topprobs.items())
                            topk_tokens = [(tok[0], score) for (tok_str, score), tok in zip(topk_tokens, await self.tokenize_list([s for s,_ in topk_tokens]))]
                            topk_tokens += [(tokens[0], scores)]
                            topk_tokens = list(dict.fromkeys(topk_tokens))
                            topk_tokens = sorted(topk_tokens, key=lambda x: x[1], reverse=True)
                            topk_tokens = topk_tokens[:logprobs]
                            
                            tokens = [tok for tok, _ in topk_tokens]
                            scores = [score for _, score in topk_tokens]
                            edge_type = ["top-{}".format(i+1) for i in range(len(topk_tokens))]
                        
                        # future continuation
                        response_buffer = response_buffer[1:]
                        continuation = CompletionResult(response_buffer, completion_result.continuation_type, completion_result.logit_mask_or_fixed_id)

                        if continuation.continuation_type is None:
                            edge_type = None

                        user_data = {
                            "openai-continuations": {
                                continuation.continuation_type: continuation
                            }
                        }
                        yield (s, tokens, scores, edge_type, user_data)
                    except IndexError:
                        break
                # print("fully expanded speculativate continuation:", [await self.detokenize(tokens)], flush=True)
                # if len(tokens) > 1:
                #     await self.cache(s, tokens, scores, edge_type)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print("error in expand_and_cache worker:", e, flush=True)
        self.register_token_stream(token_stream)

    async def argmax(self, sequences, **kwargs):
        return await self.sample(sequences, num_samples=1, temperature=0, **kwargs)

    def report_stats(self, printer, decoder_step=None):
        if printer is None:
            return
        if hasattr(printer, "report_model_stats"):
            s = openai.Completion.get_stats()
            data = {
                "tokens": s.tokens,
                "model": self.model_identifier,
                "req.": s.requests,
                "avb": f"{float(s.sum_batch_size)/max(1,s.requests):.2f}",
            }
            if decoder_step is not None:
                data["_step"] = decoder_step
            printer.report_model_stats(**data)

    async def sample(self, sequences, num_samples=1, **kwargs):
        """
        Returns a pool with `n` sampled successor nodes per node in the pool.
        """
        kwargs = {**self.model_args, **kwargs}

        async def op_sample(seqs):
            completions: List[CompletionResult] = await self.completion_buffer(seqs, logprobs=1, **kwargs)
            
            next_token_ids = []
            next_token_scores = []
            logits = []
            continuation_buffers: List[CompletionResult] = []

            for s, completion in zip(seqs, completions):
                assert not await completion.buffer.empty(), "Completion buffer is empty {}".format(completion.buffer)
                complete_data = (await completion.buffer.get(0))

                # store pointer to continuation buffers in newly expanded nodes
                continuation = CompletionResult(completion.buffer[1:], completion.continuation_type, completion.logit_mask_or_fixed_id)
                continuation_buffers.append(continuation)

                # detect fixed results (i.e. deterministic tokens)
                if "fixed" in complete_data.keys():
                    next_token = complete_data["logprobs"]["tokens"]
                    next_token_score = complete_data["logprobs"]["token_logprobs"]
                    next_token_ids.append(np.array([next_token], dtype=np.int64))
                    next_token_scores.append(np.array([next_token_score], dtype=np.float32))
                    
                    full_logits = np.ones(self.model.get_tokenizer().model_vocab_size) * np.finfo(np.float32).min
                    if next_token < len(full_logits):
                        full_logits[next_token] = next_token_score
                    # else: 
                    #  next_token is a special token, which is not in the vocab
                    logits.append(full_logits)
                    continue

                # get sampled token and score
                next_token = complete_data["logprobs"]["tokens"][0]
                next_token_score = complete_data["logprobs"]["token_logprobs"]
                
                probs = sorted(list(complete_data["logprobs"]["top_logprobs"].items()))
                logprobs = [p[1] for p in probs]
                tokens = [p[0] for p in probs]
                prob_tokens = await self.tokenize_list(tokens)
                token_ids = np.array(prob_tokens, dtype=np.int64).reshape(-1)

                full_logits = np.ones(self.model.get_tokenizer().model_vocab_size) * np.finfo(np.float32).min
                full_logits[token_ids] = np.array(logprobs)
                full_logits[next_token] = np.finfo(np.float32).min
                assert kwargs.get("temperature", 1.0) != 0.0 or np.all(full_logits < next_token_score), "next token score is not the highest"


                # retroactively apply logits mask to logits
                mask = completion.logit_mask_or_fixed_id
                if mask is None:
                    pass
                elif type(mask) is int: 
                    full_logits[mask] = np.finfo(np.float32).min
                else: 
                    full_logits[mask < 0] = np.finfo(np.float32).min

                additional_sampled_token_ids, _ = nputil.multinomial(full_logits, num_samples=num_samples - 1)

                seq_next_token_ids = np.concatenate([np.array(next_token).reshape(1), additional_sampled_token_ids], axis=0)
                full_logits[next_token] = next_token_score
                # seq_next_token_scores = full_logits.gather(-1, seq_next_token_ids)
                seq_next_token_scores = np.take_along_axis(full_logits, seq_next_token_ids, axis=-1)

                next_token_ids.append(seq_next_token_ids)
                next_token_scores.append(seq_next_token_scores)
                logits.append(full_logits)

            logits = logits
            next_token_ids = next_token_ids
            next_token_scores = next_token_scores

            def successor_user_data(continuation_buffer: SequenceResult, num_successors):
                default_user_data = {}
                if continuation_buffer.continuation_type is None:
                    return [default_user_data.copy()] * num_successors
                continuation_as_user_data = {
                    "openai-continuations": {
                        continuation_buffer.continuation_type: continuation_buffer
                    },
                    **(default_user_data.copy())
                }
                return [continuation_as_user_data] + [default_user_data.copy()] * (num_successors - 1)

            return [s.make_successors(next_token_ids[i], next_token_scores[i], logits=logits[i], 
                user_data=successor_user_data(continuation_buffers[i], len(next_token_ids[i]))) for i,s in enumerate(seqs)]
        with self.stats.timer("sample"):
            return await sequences.aelement_wise(op_sample)

    async def topk_continuations(self, sequences, k, **kwargs):
        """
        Returns a pool with `n` sampled successor nodes per node in the pool.
        """
        assert k <= 5, "The OpenAI API only supports topk probabilities with k <= 5"
        assert k >= 1, "topk_continuations() requires k >= 1"
        
        assert not "turbo" in self.model_identifier, f"Chat API models do not support topk_continuations which is required for the requested decoding algorithm, use 'sample' or 'argmax' instead."

        kwargs = {**self.model_args, **kwargs}
        kwargs.update({"temperature": 0.0})
        
        async def op_topk(seqs):
            completions: List[CompletionResult] = await self.completion_buffer(seqs, logprobs=k, **kwargs)
            
            next_token_ids = []
            next_token_scores = []
            logits = []
            continuation_buffers: List[CompletionResult] = []

            for s, completion in zip(seqs, completions):
                complete_data = (await completion.buffer.get(0))
                # store pointer to continuation buffers in newly expanded nodes
                continuation = CompletionResult(completion.buffer[1:], completion.continuation_type, completion.logit_mask_or_fixed_id)
                continuation_buffers.append(continuation)

                # detect fixed results (i.e. deterministic tokens)
                if "fixed" in complete_data.keys():
                    next_token = complete_data["logprobs"]["tokens"]
                    next_token_score = complete_data["logprobs"]["token_logprobs"]
                    next_token_ids.append(np.array([next_token], dtype=np.int64))
                    next_token_scores.append(np.array([next_token_score], dtype=np.float32))
                    
                    full_logits = np.ones(self.model.get_tokenizer().model_vocab_size) * np.finfo(np.float32).min
                    full_logits[next_token] = next_token_score
                    logits.append(full_logits)
                    continue

                # get sampled token and score
                next_token = complete_data["logprobs"]["tokens"][0]
                next_token_score = complete_data["logprobs"]["token_logprobs"]
                
                probs = sorted(list(complete_data["logprobs"]["top_logprobs"].items()), key=lambda x: x[1], reverse=True)
                logprobs = [p[1] for p in probs]
                tokens = [p[0] for p in probs]
                token_ids = np.array([self.model.get_tokenizer()(t)["input_ids"][0] for t in tokens], dtype=np.int64)

                assert token_ids[0] == next_token, f"top1 logprob token is not the same as the predicted token {token_ids[0]} (top1) != {next_token} (predicted)"

                full_logits = np.ones(self.model.get_tokenizer().model_vocab_size) * np.finfo(np.float32).min
                full_logits[token_ids] = np.array(logprobs)

                # retroactively apply logits mask to logits
                mask = completion.logit_mask_or_fixed_id
                if mask is None: pass
                elif type(mask) is int: full_logits[mask] = np.finfo(np.float32).min
                else: full_logits[mask < 0] = np.finfo(np.float32).min
                
                # make sure all token_ids are unique
                token_ids = np.array(list(set(token_ids)))

                # re-determine logprobs with logits mask applied
                logprobs = np.take_along_axis(full_logits, token_ids, axis=-1)

                next_token_ids.append(token_ids)
                next_token_scores.append(logprobs)
                logits.append(full_logits)

            def successor_user_data(continuation_buffer: SequenceResult, num_successors):
                default_user_data = {}
                if continuation_buffer.continuation_type is None:
                    return [default_user_data.copy()] * num_successors
                continuation_as_user_data = {
                    "openai-continuations": {
                        continuation_buffer.continuation_type: continuation_buffer
                    },
                    **(default_user_data.copy())
                }
                return [continuation_as_user_data] + [default_user_data.copy()] * (num_successors - 1)

            return [s.make_successors(next_token_ids[i], next_token_scores[i], logits=logits[i], 
                user_data=successor_user_data(continuation_buffers[i], len(logits[i]))) for i,s in enumerate(seqs)]
        
        with self.stats.timer("topk"):
            return await sequences.aelement_wise(op_topk)

class Struct:
    def __init__(self, **entries):
        for k, v in entries.items():
            if isinstance(v, dict):
                entries[k] = Struct(**v)
            if isinstance(v, list):
                entries[k] = [Struct(**i) if isinstance(i, dict) else i for i in v]
        self.__dict__.update(entries)
    
    def __getitem__(self, k):
        return self.__dict__[k]

    # make json serializable
    def __repr__(self):
        return str(self.__dict__)

class OpenAIModelOutputBuffer:
    def __init__(self, complete_result: CompleteTask, n, tokenizer):
        self.n = n
        self.complete_result: CompleteTask = complete_result
        self.res = complete_result.result
        self.tokenizer = tokenizer
        
        self.tokens = [[] for _ in range(n)]
        self.logprobs = [[] for _ in range(n)]
        self.response_data = [[] for _ in range(n)]

        self.preview = None

    @staticmethod
    def fixed_output(token_id, logprob):
        async def data():
            yield Struct(**{
                "tokens": [token_id],
                "logprobs": {
                    "tokens": [token_id],
                    "token_logprobs": [logprob]
                },
                "fixed": True
            })

        return CompleteTask(lambda: data(), data(), continuation_type=None, logit_mask_or_fixed_id=token_id)

    def text_to_tokens(self, l):
        if len(l) == 0 and type(l) is list:
            return []
        if type(l[0]) is int:
            # handles fixed_output case
            return l
        else:
            # handles actual API case
            text = "".join(l)
            return self.tokenizer(text)["input_ids"]

    def skip_items(self, skip=None):
        if skip is None:
            return

        def minimum_token_count_reached():
            return all(len(t) >= skip[i] for i,t in enumerate(self.tokens))

        # skip as many items as needed to reach the previous token count per sequence
        while not minimum_token_count_reached():
            self.process_next_result(next(self.res))

    def process_next_result(self, c):
        # print("data is", data)
        # choices = data.choices
        # assert len(choices) == self.n, f"OpenAI model returned different number of choices than expected: {len(choices)} != {self.n}\n\n {json.dumps(data)}"
        # index = int(c["index"])
        index = 0
        assert self.n == 1, "ModelOutputBuffer only supports n=1"
        self.tokens[index] += self.text_to_tokens(c.logprobs.tokens)
        self.logprobs[index] += c.logprobs.token_logprobs
        self.response_data[index] += [c] * len(c.logprobs.token_logprobs)

    async def advance_stream_iter(self, skip=None):
        try:
            # check if self.res is still coroutine
            if inspect.iscoroutine(self.res):
                self.res = aiter(await self.res)
            # self.skip_items(skip)
            self.process_next_result(await anext(self.res))
            return False
        except StopIteration:
            return True
        except openai.error.APIError as e:
            print("OpenAI API error: ", e, ". Retrying...", flush=True)
            # print("retry with", self.complete_result, "and offset", len(self.tokens), flush=True)
            # re-run underlying complete operation
            self.complete_result = await self.complete_result.run(retries=1)
            self.res = self.complete_result.result
            
            return await self.advance_stream_iter(skip=[len(t) for t in self.tokens])
        except openai.error.ServiceUnavailableError:
            print("OpenAI API Overloaded error: ", e, ". Retrying...", flush=True)
            # print("retry with", self.complete_result, "and offset", len(self.tokens), flush=True)
            # re-run underlying complete operation
            self.complete_result = await self.complete_result.run(retries=1)
            self.res = self.complete_result.result
            
            return await self.advance_stream_iter(skip=[len(t) for t in self.tokens])

    def buffer(self, seq_idx):
        return SequenceResultBuffer(seq_idx, self)

    def view(self, seq_idx):
        return SequenceResult(self, seq_idx)

class FixedBuffer:
    def __init__(self, values):
        self.values = values
    
    async def pop(self):
        return self.values.pop(0)
    
    async def at_end(self):
        return len(self.values) == 0

def fixed(values):
    return FixedBuffer(values)

class EmptyBuffer:
    def at_end(self):
        return True

    async def pop(self):
        assert False, "cannot pop() on empty buffer"

def empty():
    return EmptyBuffer()

class SequenceResultBuffer:
    def __init__(self, i: int, request_buffer: OpenAIModelOutputBuffer):
        self.request_buffer = request_buffer
        self.i = i
        self.items = []
    
    async def pop(self):
        await self.advance_stream_iter(self.id)
        if len(self.request_buffer.tokens[self.i]) == 0:
            raise StopIteration(f"No more tokens in buffer for sequence index {self.i}.")
        return self.request_buffer.tokens[self.i].pop(0), self.request_buffer.logprobs[self.i].pop(0)

    async def advance_stream_iter(self, index):
        # advance stream iter until we have at least one token for this sequence 
        # or the stream ends
        is_done = False
        while not is_done and len(self.request_buffer.tokens[index]) == 0:
            is_done = await self.request_buffer.advance_stream_iter()

    async def at_end(self):
        await self.advance_stream_iter(self.i)
        return len(self.request_buffer.tokens[self.i]) == 0

@dataclass
class OpenAITokenResult:
    token: int
    logprobs: Any
    data: Any

class SequenceResult:
    def __init__(self, request_buffer, result_index: int, offset: int = 0, length: int = None):
        self.request_buffer: OpenAIModelOutputBuffer = request_buffer
        self.result_index = result_index
        self.offset = offset
        self.length = length

        self.collected_data = []
        self.collected_tokens = []
        self.collected_logprobs = []

    @property
    def continuation_type(self):
        return self.request_buffer.complete_result.continuation_type

    def __getitem__(self, key):
        if type(key) is slice:
            return self.slice(key.start, key.stop)
        elif type(key) is int:
            return self.get(key)
        else:
            raise TypeError(f"Can only subscript SequenceResult with int or slice, not {type(key)}")
    
    async def json(self):
        return f"<SequenceResult current_len={self.current_len}>"

    @property
    def current_len(self):
        return max(0, len(self.request_buffer.tokens[self.result_index]) - self.offset)
    

    async def get(self, i: int):
        i = self.offset + i
        while len(self.request_buffer.response_data[self.result_index]) <= i:
            await self.request_buffer.advance_stream_iter()
        
        return OpenAITokenResult(self.request_buffer.tokens[self.result_index][i],
                                 self.request_buffer.logprobs[self.result_index][i],
                                 self.request_buffer.response_data[self.result_index][i])

    def slice(self, lower, upper):
        assert upper is None, "cannot specify upper bound for SequenceResult slice"
        return SequenceResult(self.request_buffer, self.result_index, self.offset + lower, upper)

    async def empty(self):
        if len(self.request_buffer.tokens[self.result_index]) > self.offset:
            return False
        # iterate stream until current_len is greater 0 or the stream ends
        while self.current_len == 0:
            at_end = await self.request_buffer.advance_stream_iter()
            if at_end: break
        return self.current_len == 0

class OptimisticChunkBasedOpenAIModel:
    def __init__(self, model_identifier, tokenizer):
        self.model_identifier = model_identifier.split("openai/",1)[1]
        self.chunk_size = 32
        self.nostop = False
        self.tokenizer = tokenizer

        self.input_ids = []
        self.next_token_scores = []
        self.logits_mask = []
        
        self.buffer = []

        self.num_calls = 0

    async def tokenize(self, *args, **kwargs):
        def task():
            return self.tokenizer.encode(*args, **kwargs)
        return await asyncio.get_event_loop().run_in_executor(None, task)
    
    async def detokenize(self, *args, **kwargs):
        def task():
            return self.tokenizer.decode(*args, **kwargs)
        return await asyncio.get_event_loop().run_in_executor(None, task)
        # return self.tokenizer.decode(*args, **kwargs)

    def _complete(self, input_ids, temperature=0, logprobs=1):
        assert len(input_ids) == 1, f"openai model only supports batch size of 1 with logit masks, provided {len(input_ids)}."

        kwargs = {}
        if self.logits_mask[-1] is not None:
            kwargs["logit_bias"] = self.logits_mask[-1]

        kwargs = {
            "model": self.model_identifier,
            "prompt": input_ids.tolist(),
            "max_tokens": self.chunk_size,
            "temperature": temperature,
            "logprobs": logprobs,
            "user": "lmql",
            "stream": True,
            **kwargs
        }

        complete_op = lambda: openai_complete_create(**kwargs)
        return CompleteTask(complete_op, None, continuation_type=None).run(retries=3)
        
    
    async def tokenize(self, text):
        return self.tokenizer(text)["input_ids"]

    async def __aenter__(self):
        self.previous_context_model = OptimisticChunkBasedOpenAIModel.context_model

        bos_token_id = (await self.tokenize("<BOS>"))[0]
        setattr(self, "bos_token_id", bos_token_id)
        eos_token_id = (await self.tokenize("<EOS>"))[0]
        setattr(self, "eos_token_id", eos_token_id)

        OptimisticChunkBasedOpenAIModel.context_model = self
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        OptimisticChunkBasedOpenAIModel.context_model = self.previous_context_model
        self.previous_context_model = None

OptimisticChunkBasedOpenAIModel.context_model = None

class HFModelStatsAdapter:
    @property
    def consumed_tokens(self):
        return 0
    @property
    def num_queries(self):
        return 0
    @property
    def num_generate_calls(self):
        return openai.AsyncConfiguration.get_stats().sum_batch_size
    @property
    def billable_tokens(self):
        return openai.AsyncConfiguration.get_stats().tokens
    
    def reset_stats(self):
        openai.AsyncConfiguration.get_stats().reset()

    def cost_estimate(self, model):
        return openai.AsyncConfiguration.get_stats().cost_estimate(model)

def openai_model(model_identifier):
    # make sure openai org and secret are available
    import lmql.runtime.openai_secret
    
    class OpenAIModel:
        def __init__(self) -> None:
            self.model_identifier = model_identifier
            self.served_model = None
            self._tokenizer = None

            self.decoder_args = {
                "openai_chunksize": 64
            }

        def get_tokenizer(self):
            if self._tokenizer is None:
                self._tokenizer = load_tokenizer("gpt2")
            self.served_model = self
            return self._tokenizer

        def get_dclib_model(self):
            bos_token_id = self.get_tokenizer().bos_token_id
            eos_token_id = self.get_tokenizer().eos_token_id

            dc.set_dclib_tokenizer(dc.tokenizer("lmql-adapter-tokenizer", self.tokenize, self.detokenize, bos_token_id, eos_token_id))

            return DclibOpenAiModel(self, self.get_tokenizer(), **self.decoder_args)

        async def tokenize(self, text):
            return self.get_tokenizer()(text)["input_ids"]
        
        async def detokenize(self, input_ids):
            return self.get_tokenizer().decode(input_ids)

        def sync_tokenize(self, text):
            return self.get_tokenizer()(text)["input_ids"]
    return OpenAIModel