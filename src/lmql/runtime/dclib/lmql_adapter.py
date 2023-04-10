from lmql.runtime.decoder_head import DecoderHead
from lmql.runtime.rewriter import InputIdRewriter
import lmql.runtime.bopenai as openai
from dataclasses import dataclass
from typing import List, Any
from lmql.runtime.stats import Stats
import inspect

import lmql.runtime.dclib.decoders as decoders
import lmql.runtime.dclib as dc
from lmql.runtime.interrupt import interrupt

import asyncio

import numpy as np
from lmql.utils import nputil

class _DCLibDebugPrinter: pass
_DCLibDebugPrinter.printer = None

def set_dclib_debug_printer(printer):
    _DCLibDebugPrinter.printer = printer

# obsolete
class DcLibMaskLogitsProcessor:
    def __init__(self, n, tokenize, detokenize, eos_token_id, mask_logits_processor):
        self.n = n
        self.tokenize = tokenize
        self.detokenize = detokenize
        self.eos_token_id = eos_token_id
        self.mask_logits_processor = mask_logits_processor

    async def __call__(self, prompt_ids, next_token_logits, additional_logits_processor_mask=None):
        async def apply_processor(i, head_input_ids, head_next_token_logits):
            if additional_logits_processor_mask is not None and not additional_logits_processor_mask[i]:
                return head_next_token_logits
            
            return await self.mask_logits_processor(DecoderHead(i, 
                head_input_ids, -1, head_next_token_logits, 
                self.tokenize,
                self.detokenize,
                self.eos_token_id,
                self.n))
        
        tasks = [apply_processor(i, head_input_ids, head_next_token_logits) for i, (head_input_ids, head_next_token_logits) in enumerate(zip(prompt_ids, next_token_logits))]

        return np.stack(await asyncio.gather(*tasks), axis=0)

@dataclass
class DcLibTokenMaskResult:
    logits_mask: np.ndarray
    user_data: List[Any]

class DcLibMaskLogitsProcessorWithUserData:
    def __init__(self, vocab_size, n, tokenize, detokenize, eos_token_id, mask_logits_processor):
        self.vocab_size = vocab_size
        self.n = n
        self.tokenize = tokenize
        self.detokenize = detokenize
        self.eos_token_id = eos_token_id
        self.mask_logits_processor = mask_logits_processor

    async def __call__(self, input_ids, user_data=None, additional_logits_processor_mask=None):
        async def apply_processor(i, head_input_ids, head_next_token_logits) -> DcLibTokenMaskResult:
            sequence_user_data = user_data[i] if user_data is not None else None

            if additional_logits_processor_mask is not None and not additional_logits_processor_mask[i]:
                return DcLibTokenMaskResult(head_next_token_logits, sequence_user_data)

            logits_mask, updated_user_data = await self.mask_logits_processor(DecoderHead(i, 
                head_input_ids, -1, head_next_token_logits, 
                self.tokenize,
                self.detokenize,
                self.eos_token_id,
                self.n,
                user_data=sequence_user_data), return_user_data=True)

            return DcLibTokenMaskResult(logits_mask, updated_user_data)
        
        tasks = [apply_processor(i, ids, np.zeros(self.vocab_size, dtype=np.float32)) for i, ids in enumerate(input_ids)]
        tasks = await asyncio.gather(*tasks)

        return DcLibTokenMaskResult(np.stack([t.logits_mask for t in tasks], axis=0), [t.user_data for t in tasks])

class QueryDcLibAdapter:
    def __init__(self, vocab_size, tokenize, detokenize, bos_token_id, eos_token_id):
        self.vocab_size = vocab_size
        self.tokenize = tokenize
        self.detokenize = detokenize
        
        self.bos_token_id = bos_token_id
        self.eos_token_id = eos_token_id

        dc.set_dclib_tokenizer(dc.tokenizer("lmql-adapter-tokenizer", self.tokenize, self.detokenize, self.bos_token_id, self.eos_token_id))

    def make_decoder_head(self, i, initial_prompt_offset, s: dc.DecoderSequence):
        return DecoderHead(i, 
            s.input_ids, 0, 0,
            self.tokenize,
            self.detokenize,
            self.eos_token_id,
            initial_prompt_offset,
            user_data = s.user_data
        )

    async def score_distribution_values(self, prompt, values, dcmodel: dc.DcModel, **decoder_args):
        prompt_seq = dc.seq([self.bos_token_id] + await self.tokenize(prompt))
        value_ids = [await self.tokenize(value) for value in values]

        dcmodel.log_billable_tokens(sum(len(ids) + 1 for ids in value_ids) + len(value_ids) * (len(prompt_seq.input_ids)))
        dcmodel.log_queries(sum(len(ids) + 1 for ids in value_ids))

        value_scores = []
        for s, value in zip(await dcmodel.score([prompt_seq] * len(value_ids), value_ids), value_ids):
            s = s.expand()
            value_score = s.logprobs[-len(value):]
            value_scores.append(value_score)
        
        return value_scores

    async def query(self, prompt, mask_logits_processor, head_input_id_rewriter, active_prompt_rewriter, dcmodel, decoder_args, **kwargs):
        assert issubclass(type(dcmodel), dc.DcModel), "The provided dcmodel must be a subclass of DcModel"

        if "no_repeat_ngram_size" in decoder_args:
            print("warning: no_repeat_ngram_size is known to cause issues when used with constrained decoding, including non-termination.")

        prompt_ids = await self.tokenize(prompt)
        if self.bos_token_id is not None:
            prompt_ids = [self.bos_token_id] + prompt_ids
        n = len(prompt_ids)

        decoder_args = decoder_args.copy()

        # pass processor as decoder argument
        # decoder_args["additional_logits_processors"] = [DcLibMaskLogitsProcessor(n, self.tokenize, self.detokenize, self.eos_token_id, mask_logits_processor)]
        decoder_args["dclib_additional_logits_processor"] = DcLibMaskLogitsProcessorWithUserData(self.vocab_size, n, self.tokenize, self.detokenize, self.eos_token_id, mask_logits_processor)

        # setup prompt executing input id rewriter
        rewriter = InputIdRewriter(head_input_id_rewriter, self.tokenize, self.detokenize, self.eos_token_id, n)
        
        # pass rewriter as decoder argument
        decoder_args["input_id_rewriter"] = rewriter

        if "output_writer" in decoder_args:
            set_dclib_debug_printer(decoder_args["output_writer"])

        if _DCLibDebugPrinter.printer is not None:
            if hasattr(_DCLibDebugPrinter.printer, "records_graph"):
                if _DCLibDebugPrinter.printer.records_graph:
                    dc.set_record_graph()

        mode = decoder_args["decoder"].lower()
        decoder_fct = dc.get_decoder(mode)
        self.validate_args(decoder_args, decoder_fct)

        # alias max_length -> max_len
        if "max_length" in decoder_args:
            decoder_args["max_len"] = decoder_args["max_length"]

        # setup dcmodel for use
        dcmodel.model_args = decoder_args
        decoder_args["dcmodel"] = dcmodel
        dc.set_truncation_threshold(dcmodel.truncation_threshold)

        step_budget = decoder_args.get("step_budget", 1024)
        
        async def debug_out(decoder_step):
            if _DCLibDebugPrinter.printer is not None and dc.DecoderSequence.graph is not None:
                data = await dc.DecoderSequence.graph.json(diff=True)
                data = replace_inf_nan_with_str(data)
                _DCLibDebugPrinter.printer.add_decoder_state(data)
            dcmodel.report_stats(_DCLibDebugPrinter.printer, decoder_step)

        try:
            import time

            decoder_step = 0
            average_step_time = None
            start = time.time()
            async for _ in decoder_fct(prompt_ids, **decoder_args):
                await debug_out(decoder_step)
                decoder_step += 1

                if step_budget is not None and decoder_step >= step_budget:
                    print("warning: step budget exceeded")
                    break

                if interrupt.check():
                    interrupt.clear()
                    raise InterruptedError("lmql.runtime.interrupt")
                
                average_step_time = (time.time() - start) if average_step_time is None else (average_step_time * 0.9 + (time.time() - start) * 0.1)

                if "performance_stats" in decoder_args:
                    if decoder_step % 10 == 0:
                        Stats.print_all()
                        print("step", decoder_step, "time", average_step_time)

                start = time.time()
                
        except dc.FinishException as fe:
            # one last call to debug_out to get the final state
            await debug_out(decoder_step)
            # if dc.finish is used, the decoder sets the sequences it considers 
            # finished (return them to prompt interpreter)
            result_sequences = fe.result_sequences
            
            billable_tokens = 0
            for s in result_sequences:
                upper = len(s.input_ids)
                has_deterministic_tail = False
                while s.deterministic[upper-1]:
                    upper -= 1
                    has_deterministic_tail = True
                # +1 for the eos token
                billable_tokens += upper + (1 if has_deterministic_tail else 0)
            
            dcmodel.log_billable_tokens(billable_tokens)
            
            return [self.make_decoder_head(i,n,s) for i,s in enumerate(result_sequences)]
    
    def validate_args(self, decoder_args, decoder_fct):
        INTERNAL_ARGS = ["decoder", "dcmodel", "dclib_additional_logits_processor", "input_id_rewriter", "output_writer", "chatty_openai", "distribution_batch_size", "openai_chunksize", "step_budget", "stats", "performance_stats"]

        # get all arg names and kwarg names of decoder function
        decoder_arg_names = inspect.getfullargspec(decoder_fct).args
        decoder_kwarg_names = inspect.getfullargspec(decoder_fct).kwonlyargs
        for k in decoder_args.keys():
            if k not in decoder_arg_names and k not in decoder_kwarg_names and k not in INTERNAL_ARGS:
                raise ValueError("Unknown decoder argument: {}".format(k))

def replace_inf_nan_with_str(d):
    import math

    if type(d) is dict:
        for k, v in d.items():
            d[k] = replace_inf_nan_with_str(v)
        return d
    elif type(d) is list:
        for i, v in enumerate(d):
            d[i] = replace_inf_nan_with_str(v)
        return d
    elif type(d) is float:
        if math.isinf(d) or math.isnan(d):
            return str(d)
    return d
