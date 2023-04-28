import asyncio
from collections import namedtuple
from typing import List, Union

from .dclib_array import DataArray
from .dclib_rewrite import DcModelRewriteMixin
from .dclib_global import stats
from .dclib_seq import DecoderSequence, detseq, deepcopy, deepmerge, DecoderSequence, DeterministicDecoderSequence, Continuation
import numpy as np
from lmql.utils import nputil
import lmql.runtime.masks as masks
from dataclasses import dataclass
import sys

from lmql.runtime.stats import Stats

@dataclass
class DcModelLogitsTask:
    model: any
    input_ids: np.ndarray
    logits_mask: np.ndarray
    kwargs: dict
    result_fut: asyncio.Future

class ModelQueue:
    @staticmethod
    def get(model_identifier, vocab_size):
        if model_identifier not in ModelQueue._instances.keys():
            ModelQueue._instances[model_identifier] = ModelQueue(model_identifier, vocab_size)
        return ModelQueue._instances[model_identifier]
    
    def __init__(self, model_identifier, vocab_size):
        self.model_identifier = model_identifier
        self.logits_queue = asyncio.Queue()
        self.vocab_size = vocab_size
        self.logits_workers = [asyncio.create_task(self.queue_worker_logits()) for _ in range(8)]
    
    def __del__(self):
        for w in self.logits_workers:
            w.cancel()
        
    def put(self, task):
        self.logits_queue.put_nowait(task)
    
    async def queue_worker_logits(self):
        max_batch_size = DcModel.batch_size
        while True:
            try:
                batch: List[DcModelLogitsTask] = []
                task = await self.logits_queue.get()
                batch.append(task)
                if self.logits_queue.qsize() == 0:
                    await asyncio.sleep(0.05)

                while len(batch) < max_batch_size:
                    try:
                        task = self.logits_queue.get_nowait()
                        batch.append(task)
                    except asyncio.QueueEmpty:
                        break
                
                # group by parameters
                groups = [[]]
                for t in batch:
                    if len(groups[-1]) == 0:
                        groups[-1].append(t)
                        continue
                    current_group_model = groups[-1][0].model
                    current_group_kwargs = str(groups[-1][0].kwargs)
                    if t.model == current_group_model and str(t.kwargs) == current_group_kwargs:
                        groups[-1].append(t)
                    else:
                        groups.append([t])

                # run groups in batches
                for group in groups:
                    kwargs = group[0].kwargs
                    model = group[0].model
                    logits, raw = await model.logits(
                        [task.input_ids for task in group],
                        logits_mask=self.stack_logit_masks([task.logits_mask for task in group]),
                        **kwargs
                    )
                    for logits, raw, fut in zip(logits, raw, [task.result_fut for task in group]):
                        fut.set_result((logits, raw))
                    # print("batch of size", len(group), len(batch), self.logits_queue.qsize(), flush=True)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print("Exception in queue worker logits: ", e)

    def stack_logit_masks(self, logit_masks):
        if all([m is None for m in logit_masks]):
            return None
        else:
            # TODO: return logprob 0 for eos mask
            for i in range(len(logit_masks)):
                if masks.is_fixed_int_mask(logit_masks[i]):
                    logit_masks[i] = masks.to_dense(logit_masks[i], self.vocab_size)
                elif type(logit_masks[i]) is np.int64:
                    logit_masks[i] = masks.to_dense(nputil.ensure_array(logit_masks).reshape(1), self.vocab_size)
                elif type(logit_masks[i]) is int:
                    logit_masks[i] = masks.to_dense(nputil.ensure_array(logit_masks).reshape(1), self.vocab_size)
                else:
                    assert len(logit_masks[i]) == self.vocab_size
            lm = np.stack([m if m is not None else np.zeros((self.vocab_size), dtype=np.bool) for m in logit_masks])
            return lm

ModelQueue._instances = {}

class DcModel(DcModelRewriteMixin):
    def __init__(self, model, tokenizer, truncation_threshold=-3e38, init_workers=True, **kwargs):
        """
        Parameters:
        
        model: The model to use for inference.
        bos_token_id: The token id to use for the beginning of a sequence.
        eos_token_id: The token id to use for the end of a sequence.
        truncation_threshold: The threshold to use for logit truncation (cf. DecoderSequence.truncation_threshold). Logits below this threshold are considered to be -inf and will never be considered as next token.
        """
        self.model = model
        self.tokenizer = tokenizer
        self.model_identifier = model.model_identifier
        self.model_args = kwargs

        self.bos_token_id = tokenizer.bos_token_id
        self.eos_token_id = tokenizer.eos_token_id
        self.truncation_threshold = truncation_threshold

        self.stats = Stats("dcmodel")

        if init_workers: self.logits_queue = ModelQueue.get(self.model_identifier, self.tokenizer.vocab_size)
        else: self.logits_queue = None

    def log_billable_tokens(self, n: int):
        if hasattr(self.model, "billable_tokens"):
            self.model.billable_tokens += n
        
    def log_queries(self, n: int):
        if hasattr(self.model, "num_queries"):
            self.model.num_queries += n

    async def detokenize(self, *args, **kwargs):
        return await self.model.detokenize(*args, **kwargs)
    
    async def tokenize(self, *args, **kwargs):
        return await self.model.tokenize(*args, **kwargs)

    async def model_logits_async(self, model, input_ids, logits_mask=None, **kwargs):
        loop = asyncio.get_running_loop()
        result_fut = loop.create_future()
        
        # print(kwargs)
        model_args = {
            "temperature": kwargs.get("temperature", None),
            "eos_token_id": kwargs.get("eos_token_id", None),
        }
        
        self.logits_queue.put(DcModelLogitsTask(model, input_ids, logits_mask, model_args, result_fut))

        return await result_fut

    async def autobatch_logits_with_cache(self, model, input_ids, max_batch_size, cache=None, logits_mask=None, **kwargs):
        kwargs = {**self.model_args, **kwargs}

        if cache is not None: 
            input_ids_to_process = [ids for cache, ids in zip(cache, input_ids) if cache is None]
        else: 
            input_ids_to_process = input_ids

        # automatic batching
        results = await asyncio.gather(*[self.model_logits_async(
            model, 
            input_ids_to_process[i],
            logits_mask=logits_mask[i] if logits_mask is not None else None,
            eos_token_id=self.eos_token_id,
            **model.model_kwargs,
            **kwargs
        ) for i in range(len(input_ids_to_process))])

        # call model only for non-cached input_ids
        processed_logits = np.stack([r[0] for r in results], axis=0)
        processed_logits_raw = np.stack([r[1] for r in results], axis=0)

        # shortcut if no cache
        if cache is None: return processed_logits, processed_logits_raw

        # merge with cache
        result_logits = []
        result_raw = []
        ptr = 0
        for c in cache:
            if c is not None:
                result_logits.append(c[0])
                result_raw.append(c[1])
            else:
                result_logits.append(processed_logits[ptr])
                result_raw.append(processed_logits_raw[ptr])
                ptr += 1
        
        return np.stack(result_logits, axis=0), np.stack(result_raw, axis=0)

    async def compute_logits_mask(self, input_ids, user_data, is_constrained, seqs, required=False, **kwargs):
        if "modern_logits_processor" in kwargs:
            processor = kwargs["modern_logits_processor"]
            mask = await processor(seqs, additional_logits_processor_mask=is_constrained, **kwargs)
            return mask

        assert not required, "compute_logits_mask() cannot produce a token mask, as the provided kwargs do not contain a logits processor. Please make sure to pass a logits processor to decoding function you are using."
        return namedtuple("LogitsMaskResult", ["logits_mask", "user_data"])([None], user_data)

    async def logits(self, seqs, max_batch_size=16, **kwargs):
        with self.stats.timer("logits"):
            input_ids = [s.input_ids for s in seqs]
            user_data = [s.data() for s in seqs]
            cache = [(s.logits, s.raw_logits) if s.logits is not None else None for s in seqs]

            # determine set of sequences that are constrained
            constrained_seqs = np.array([s.is_query_constrained for s in seqs], dtype=np.bool_)

            # compute logits mask
            logits_mask_result = await self.compute_logits_mask(input_ids, user_data, constrained_seqs, seqs, **kwargs)
            logits_mask = logits_mask_result.logits_mask
            if len(logits_mask) == 1 and logits_mask[0] is None: logits_mask = None
            
            # update user data with new information obtained when computing logits masks
            for s, updated_user_data in zip(seqs, logits_mask_result.user_data):
                if updated_user_data is None: continue
                # TODO: update instead of reassign
                s.user_data = updated_user_data
                s.user_data["set_by"] = "where"

            # compute logits with automatic batching
            result_logits, result_raw = await self.autobatch_logits_with_cache(self.model, input_ids, max_batch_size=max_batch_size, cache=cache, logits_mask=logits_mask, **kwargs)

            # cache logits in nodes (if self.input_ids is used)
            for s,logits,raw in zip(seqs, result_logits, result_raw):
                s.logits = logits
                s.raw_logits = raw
            
            return result_logits, result_raw

    async def argmax(self, sequences, **kwargs):
        """
        Returns a pool with `n` sampled successor nodes per node in the pool.
        """
        kwargs = {**self.model_args, **kwargs}

        async def op_argmax(seqs):
            if len(seqs) == 0:
                return []
            
            if all(type(s) is DeterministicDecoderSequence for s in seqs) and all(len(s.next_ids) > 0 for s in seqs):
                next_token_ids = np.array([s.next_ids[0] for s in seqs])
                next_token_scores = np.array([s.next_logprobs[0] for s in seqs])
                return [s.make_successors(next_token_ids[i].reshape(1), next_token_scores[i], logits=None) for i,s in enumerate(seqs)]
            
            self.model.num_queries += len(seqs)
            logits, raw_logits = await self.logits(seqs, **kwargs)

            next_token_ids = logits.argmax(axis=-1)
            next_token_scores = np.take_along_axis(logits, next_token_ids.reshape(-1,1), axis=-1)
            return [s.make_successors(next_token_ids[i].reshape(1), next_token_scores[i], logits=raw_logits[i]) for i,s in enumerate(seqs)]
        
        return await sequences.aelement_wise(op_argmax)


    async def score(self, sqs: List[DecoderSequence], tokens: List[List[int]], max_batch_size=None, deterministic: Union[bool, List[bool]]=False, stop_phrase=False, needs_rewrite=True, user_data=None, noscore=False, internal=False):
        with self.stats.timer("score"):
            assert len(sqs) == len(tokens), "Number of sequences and number of tokens to be scored must match, but got {} and {}".format(len(sqs), len(tokens))
            
            if max_batch_size is None:
                max_batch_size = DcModel.batch_size

            def make_detseq(s, token_score, completion):
                # compose deterministic flags
                if type(deterministic) is bool:
                    deterministic_flags = np.concatenate([s.deterministic, np.array([deterministic])])
                    next_deterministic = np.array([deterministic] * len(completion[1:]))
                else:
                    assert type(deterministic) is list and len(deterministic) == len(completion), "If deterministic is a list, it must have the same length as the number of tokens to be scored"
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
            async for s,c,ts in self.score_tokens(sqs, tokens, max_batch_size=max_batch_size, noscore=noscore):
                results.append(make_detseq(s, ts[:len(c)], c))
            return results
        
    async def score_tokens(self, sqs: List[DecoderSequence], tokens: List[List[int]], max_batch_size=None, noscore=False):
        """
        Iterates the scores for 'tokens' when appended to the sequences in 'sqs', element-wise.

        Returns:
            List of tuples (sqs[i], tokens[i], scores(token[i]))
        """

        if max_batch_size is None:
            max_batch_size = DcModel.batch_size

        completion = [np.array(cont) for cont in tokens]

        for i in range(0, len(sqs), max_batch_size):
            batch_sqs = sqs[i:i+max_batch_size]
            batch_input_ids = np.stack([s.input_ids for s in batch_sqs], axis=0)
            batch_completion = np.stack(self.model.right_pad(completion[i:i+max_batch_size], pad_token_id=self.eos_token_id)["input_ids"], axis=0)

            if noscore:
                token_scores = np.zeros_like(batch_completion)
            else:
                token_scores, _ = await self.model.score(
                    batch_input_ids,
                    batch_completion,
                    eos_token_id=self.eos_token_id
                )
            for s,c,ts in zip(batch_sqs,completion[i:i+max_batch_size], token_scores):
                yield (s,c,ts)

    async def score_old(self, seqs: Union[DataArray, DecoderSequence], tokens: Union[List[int], List[List[int]]], max_batch_size=4, deterministic=False, stop_phrase=False):
        if type(tokens[0]) is int:
            tokens = [tokens]
        
        unwrap = False
        if type(seqs) is DecoderSequence:
            seqs = DataArray([seqs] * len(tokens))
            unwrap = True
        
        sqs = list(seqs.items())
        original_shape = seqs.shape
        seqs = seqs.flatten()
        assert len(sqs) == len(tokens), "Number of sequences and number of tokens to be scored must match, but got {} and {}".format(len(sqs), len(tokens))

        input_ids = np.stack([s.input_ids for s in sqs], axis=0)
        completion = [np.array(cont) for cont in tokens]

        all_token_scores = []
        all_logits = []
        all_completions = []

        # automatic batching
        for i in range(0, len(input_ids), max_batch_size):
            batch_completion = np.stack(self.model.right_pad(completion[i:i+max_batch_size], pad_token_id=self.eos_token_id)["input_ids"], axis=0)
            
            token_scores, logits = await self.model.score(
                input_ids[i:i+max_batch_size],
                batch_completion,
                eos_token_id=self.eos_token_id
            )
            for c,ts,logs in zip(completion[i:i+max_batch_size], token_scores, logits):
                all_completions.append(c)
                all_token_scores.append(ts[:len(c)])
                all_logits.append(logs[:len(c)])

        def make_detseq(s, token_score, logits, completion, user_data):
            return detseq(ids=np.concatenate([s.input_ids, completion[:1]], axis=0), 
                    next_ids=completion[1:],
                    logprobs=np.concatenate([s.logprobs, token_score[:1]], axis=0),
                    next_logprobs=token_score[1:],
                    deterministic=np.concatenate([s.deterministic, np.array([deterministic])]),
                    next_deterministic=np.array([deterministic] * len(completion[1:])),
                    predecessor=s,
                    user_data=user_data,
                    stop_phrase=np.concatenate([s.stop_phrase, np.array([stop_phrase])]),
                    needs_rewrite=True,
                    sticky_user_data_keys=s.sticky_user_data_keys)

        s = DataArray([make_detseq(s, token_score, logits, completion, s.user_data) for s,token_score,logits,completion in zip(sqs, all_token_scores, all_logits, all_completions)])
        
        if unwrap: 
            return list(s.items())
        else:
            return s.reshape(original_shape)

    async def sample(self, sequences, num_samples=1, **kwargs):
        """
        Returns a pool with `n` sampled successor nodes per node in the pool.
        """
        kwargs = {**self.model_args, **kwargs}

        async def op_sample(seqs):
            if len(seqs) == 0:
                return []

            logits, raw_logits = await self.logits(seqs, **kwargs)
            vocab_size = logits.shape[-1]

            next_token_ids = []
            next_token_scores = []

            for i in range(len(logits)):
                probs = np.exp(logits[i])
                num_possible = (probs > 0).sum()
                token_ids = np.random.choice(vocab_size, size=min(num_samples, num_possible), p=probs, replace=False)
                next_token_ids.append(token_ids)
                next_token_scores.append(np.take_along_axis(logits[i], token_ids, axis=-1))

            return [s.make_successors(next_token_ids[i], next_token_scores[i], logits=raw_logits[i]) for i,s in enumerate(seqs)]
        
        return await sequences.aelement_wise(op_sample)

    async def topk_continuations(self, sequences, k, **kwargs):
        kwargs = {**self.model_args, **kwargs}

        async def op_topk(path, seqs, k):
            if len(seqs) == 0:
                return path, []

            logits, raw_logits = await self.logits(seqs, **kwargs)

            next_token_scores, next_tokens = nputil.topk(
                logits, k, sorted=True, axis=1
            )

            return path, [s.make_successors(next_tokens[i], next_token_scores[i], logits=raw_logits[i]) for i,s in enumerate(seqs)]

        result_items = await asyncio.gather(*[op_topk(path, seqs, k) for path, seqs in sequences.sequences.items()])
        return DataArray(dict(result_items))
    
    def report_stats(self, printer, decoder_step=None):
        self.model.report_stats(printer, decoder_step)

DcModel.batch_size = 1


def model(model=None, **kwargs) -> DcModel:
    if "dcmodel" in kwargs:
        return kwargs["dcmodel"]
    if issubclass(type(model), DcModel):
        model.model_args = {**model.model_args, **kwargs}
        return model
    return DcModel(model, **kwargs)

def tokenizer(name, tokenize, detokenize, bos_token_id, eos_token_id):
    class AsyncTokenizer:
        def __init__(self, eos_token_id, bos_token_id):
            self.name = name
            self.eos_token_id = eos_token_id
            self.bos_token_id = bos_token_id
        async def __call__(self, text):
            return await tokenize(text)
        async def decode(self, tokens):
            return await detokenize(tokens)
    return AsyncTokenizer(eos_token_id=eos_token_id, bos_token_id=bos_token_id)