import asyncio
import numpy as np
from .dclib_seq import deepcopy, deepmerge, DecoderSequence, DeterministicDecoderSequence, Continuation
from .dclib_array import DataArray

from typing import List, Optional, Union, Tuple, Dict, Any, Callable
from lmql.runtime.stats import Stats

stats = Stats("dclib_rewrite")

def _stripped_ids(seqs, seqidx, strip_eos):
    if strip_eos == True:
        return seqs[seqidx].input_ids[:-1]
    elif type(strip_eos) is list:
        sequence_strip = strip_eos[seqidx]
        if sequence_strip == True:
            return seqs[seqidx].input_ids[:-1]
        elif type(sequence_strip) is int:
            return seqs[seqidx].input_ids[:sequence_strip] 
        else:
            return seqs[seqidx].input_ids
    else:
        return seqs[seqidx].input_ids

def get_strip_eos(seqidx, strip_eos):
    if strip_eos == True: return True
    elif type(strip_eos) is list:
        sequence_strip = strip_eos[seqidx]
        if sequence_strip == True: return True
        elif type(sequence_strip) is int: return True
        else: return False
    else: return False

class DcModelRewriteMixin:
    async def _rewrite_seq(self, seqs_or_seq, noscore=False):
        # check self.model_args for a "modern_rewriter" key
        if "modern_rewriter" not in self.model_args:
            return seqs_or_seq
        
        # accept both a single sequence or a list of sequences
        unwrap = lambda v: v
        seqs = seqs_or_seq 
        if type(seqs_or_seq) is not list:
            seqs = [seqs_or_seq]
            unwrap = lambda v: v[0] if type(v) is list and len(v) == 1 else v

        # do not rewrite deterministic sequences (rewrite mask set to False)
        mask_seq_to_rewrite = np.array([s.needs_rewrite for s in seqs], dtype=np.bool_)

        rewriting_iterations = 0
        results = [None for _ in seqs]
        still_need_rewrite = list(zip(range(len(seqs)), seqs, mask_seq_to_rewrite))

        did_rewrite = False
        
        while len(still_need_rewrite) > 0:
            rewriting_iterations += 1
            
            indices = [i for i, _, _ in still_need_rewrite]
            seqs = [s for _, s, _ in still_need_rewrite]
            mask = [v for _, _, v in still_need_rewrite]
            
            rewriter = self.model_args["modern_rewriter"]
            rewritten_ids = await rewriter(seqs, mask)
            final_result = rewritten_ids.final

            if rewritten_ids.strip_eos[0] != False:
                did_rewrite = True

            still_need_rewrite = []
            iteration_results = await self.apply_rewrite(seqs, rewritten_ids, noscore=noscore, unwrap=unwrap)
            for i, s, done in zip(indices, iteration_results, final_result):
                results[i] = s
                if not done and s.is_done():
                    still_need_rewrite.append((i, s, mask_seq_to_rewrite[i]))
        
        # print("rewrite iterations:", rewriting_iterations)

        return unwrap(results)
    
    async def apply_rewrite(self, seqs, rewritten_ids, noscore=False, unwrap=lambda v: v):
        # update user data, if rewriter provides it
        for s, user_data in zip(seqs, rewritten_ids.user_data):
            s.user_data = deepmerge(deepcopy(s.user_data), user_data) if user_data is not None else s.user_data
            s.user_data["set_by"] = "rewrite"

        all_updated_ids = rewritten_ids.appended_input_ids
        if all_updated_ids is None:
            all_updated_ids = [None for _ in range(len(seqs))]

        # extract the offset of value tokens in appended_ids, before the sequence is deterministic
        value_offset = rewritten_ids.value_offset
        if value_offset is None:
            value_offset = [0 for _ in range(len(seqs))]

        # concat existing input_ids (minus eos if strip_eos) with appended input_ids
        rewriting_tasks = []
        for seqidx, (s, updated_ids, offset) in enumerate(zip(seqs, all_updated_ids, value_offset)):
            # run actually rewrites asynchronously
            rewriting_tasks.append(self._rewrite_seq_task(s, seqidx, seqs, rewritten_ids, updated_ids, offset, noscore=noscore))
        rewritten_seqs = [s for s in await asyncio.gather(*rewriting_tasks) if s is not None]
        return unwrap(rewritten_seqs)

    async def _rewrite_seq_task(self, s, seqidx, seqs, rewritten_ids, updated_ids, value_offset, noscore=False):
        if (updated_ids is None or len(updated_ids) == 0) and not get_strip_eos(seqidx, rewritten_ids.strip_eos):
            return s
        else:
            ids = _stripped_ids(seqs, seqidx, rewritten_ids.strip_eos)

            # if the rewritten sequence is identical to the original sequence, we can just keep the original sequence (with updated user data)
            if (updated_ids is not None) and (len(ids) == len(s.input_ids) - 1 and len(updated_ids) == 1 and updated_ids[0] == s.input_ids[-1]):
                return s
            
            # find the common prefix between the original sequence and the rewritten sequence
            continued_seq = s
            # keep track of current continuation seqs, to potentially traverse forward again (matching updated ids)
            successors = [] 
            # traverse backwards until continued_seq matches ids in length - 1
            while len(continued_seq.input_ids) > len(ids) and continued_seq.predecessor is not None:
                successors.insert(0, continued_seq)
                continued_seq = continued_seq.predecessor

            # traverse forward again, until the sequence no longer matches with updated_ids
            last_rewrite_offset = len(continued_seq.input_ids)
            offset = last_rewrite_offset
            while offset < len(successors) + last_rewrite_offset and \
                updated_ids is not None and \
                offset < len(updated_ids) and \
                successors[offset - last_rewrite_offset].input_ids[-1] == updated_ids[offset]:
                
                offset += 1
                continued_seq = successors[offset - last_rewrite_offset - 1]

            assert continued_seq is not None, "error: a rewritten sequence is not a continuation of any sequence already decoded. Going from {} to {} with common text {}".format(
                await s.text(),
                await self.detokenize(updated_ids),
                # common ids
                await self.detokenize(ids),
            )

            # align user data
            user_data = continued_seq.extend_user_data(user_data=s.user_data)

            if updated_ids is None:
                s = DecoderSequence(continued_seq.input_ids, continued_seq.logprobs, continued_seq.deterministic, stop_phrase=continued_seq.stop_phrase, 
                                    predecessor=continued_seq, user_data=user_data, sticky_user_data_keys=continued_seq.sticky_user_data_keys, epsilon_node=True)
                s.needs_rewrite = False
                return s

            # offset updated_ids to the number of tokens that are already present as continued_seq
            appended_ids = updated_ids[offset:]

            if len(appended_ids) == 0:
                return DecoderSequence(continued_seq.input_ids, continued_seq.logprobs, continued_seq.deterministic, stop_phrase=continued_seq.stop_phrase,
                                    predecessor=continued_seq, user_data=user_data, sticky_user_data_keys=continued_seq.sticky_user_data_keys, epsilon_node=True)

            # value tokens
            num_value_tokens = value_offset - offset
            deterministic = [True if i + 1 > num_value_tokens else False for i in range(len(appended_ids))]
            continuation = (await self.score([continued_seq], [appended_ids], deterministic=deterministic, stop_phrase=False, needs_rewrite=False, user_data=user_data, noscore=noscore))[0]
            
            # continuation.stop_phrase = s.stop_phrase[:len(continuation.input_ids) - 1] 
            continuation.needs_rewrite = False
            
            steps = 0
            while type(continuation) is DeterministicDecoderSequence and len(continuation.next_ids) > 0 and steps < num_value_tokens:
                continuation.user_data = deepcopy(s.predecessor.user_data)
                # print("continuation.user_data", continuation.user_data, flush=True)
                continuation = continuation.extend(Continuation(continuation.next_ids[0], continuation.next_logprobs[0], continuation.user_data))
                steps += 1
            
            continuation.user_data = rewritten_ids.rewritten_seq_user_data[seqidx] or user_data

            return continuation

    async def rewrite(self, ar: Union[DataArray, List[DecoderSequence], DecoderSequence], noscore=False):
        """
        Applies the active rewriting strategy (e.g. the LMQL interpreter) to the provided (array of) sequences.
        
        This may add, remove or change tokens in the sequence, including the EOS token.
        """
        if type(ar) is not DataArray:
            return await self._rewrite_seq(ar)

        async def op_rewrite(path, seqs):
            """
            Rewrites the sequences in the pool using the rewriting strategy provided in kwargs.

            If no rewriting strategy is provided, no rewriting is performed.
            """
            return path, await self._rewrite_seq(seqs, noscore=noscore)
        
        with stats.timer("rewrite"):
            result_items = await asyncio.gather(*[op_rewrite(path, seqs) for path, seqs in ar.sequences.items()])
        return DataArray(dict(result_items))