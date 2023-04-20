# coding=utf-8
# This file is adapted from the original file as part of the huggingface/transformers library, 
# which is licensed and distributed according to the following terms:
#
# Copyright 2020 The Google AI Language Team Authors, Facebook AI Research authors and The HuggingFace Inc. team.
# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import warnings
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union
import inspect

import torch
import torch.distributed as dist
from torch import nn

from transformers.file_utils import ModelOutput
from transformers.generation.utils import (
    EncoderNoRepeatNGramLogitsProcessor,
    ForcedBOSTokenLogitsProcessor,
    ForcedEOSTokenLogitsProcessor,
    HammingDiversityLogitsProcessor,
    InfNanRemoveLogitsProcessor,
    LogitsProcessorList,
    MinLengthLogitsProcessor,
    NoBadWordsLogitsProcessor,
    NoRepeatNGramLogitsProcessor,
    PrefixConstrainedLogitsProcessor,
    RepetitionPenaltyLogitsProcessor,
    TemperatureLogitsWarper,
    TopKLogitsWarper,
    TopPLogitsWarper,
)
from transformers.generation.stopping_criteria import (
    MaxLengthCriteria,
    MaxNewTokensCriteria,
    MaxTimeCriteria,
    StoppingCriteriaList,
    validate_stopping_criteria,
)
from transformers.utils import logging

logger = logging.get_logger(__name__)

def ensure_tensor(v):
    if torch.is_tensor(v): 
        return v
    else:
        return torch.tensor(v)
class AsyncLogitsProcessorList(list):
    """
    This class can be used to create a list of :class:`~transformers.LogitsProcessor` or
    :class:`~transformers.LogitsWarper` to subsequently process a :obj:`scores` input tensor. This class inherits from
    list and adds a specific `__call__` method to apply each :class:`~transformers.LogitsProcessor` or
    :class:`~transformers.LogitsWarper` to the inputs.
    """

    async def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, filter_processors=None, **kwargs) -> torch.FloatTensor:
        for processor in self:
            if str(type(processor)) in (filter_processors if filter_processors is not None else []):
                continue
            function_args = inspect.signature(processor.__call__).parameters
            is_async = inspect.iscoroutinefunction(processor) or inspect.iscoroutinefunction(processor.__call__)
            
            if len(function_args) > 2:
                assert all(
                    arg in kwargs for arg in list(function_args.keys())[2:]
                ), f"Make sure that all the required parameters: {list(function_args.keys())} for {processor.__class__} are passed to the logits processor."
                
                if is_async:
                    scores = await processor(input_ids, scores, **kwargs)
                else:
                    scores = processor(input_ids, scores, **kwargs)
            else:
                if is_async:
                    scores = await processor(input_ids, scores)
                else:
                    scores = processor(input_ids, scores)
        return scores

class GenerationMixin:
    """
    A class containing all of the functions supporting generation, to be used as a mixin in
    :class:`~transformers.PreTrainedModel`.
    """

    def right_pad(self, input_ids: List[torch.LongTensor], pad_token_id: int, return_attention_mask: bool = True) -> Tuple[torch.LongTensor, Optional[torch.LongTensor]]:
        lengths = set([len(x) for x in input_ids])
            
        if len(lengths) == 1:
            return {
                "input_ids": torch.stack(input_ids, dim=0)
            }

        attention_mask = torch.stack(
            [torch.tensor([1] * len(x) + [0] * (max(lengths) - len(x)), dtype=torch.long) for x in input_ids]
        )
        input_ids = torch.stack(
            [torch.cat([x, torch.tensor([pad_token_id] * (max(lengths) - len(x)), dtype=torch.long)], axis=0) for x in input_ids]
        )

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask
        }

    def prepare_inputs_for_generation(self, input_ids: torch.LongTensor, eos_token_id=None, **kwargs) -> Dict[str, Any]:
        """
        Implement in subclasses of :class:`~transformers.PreTrainedModel` for custom behavior to prepare inputs in the
        generate method.
        """
        if torch.is_tensor(input_ids):
            return {
                "input_ids": input_ids
            }
        
        if type(input_ids) is list:
            lengths = set([len(x) for x in input_ids])
            
            if len(lengths) == 1:
                return {
                    "input_ids": torch.stack(input_ids, dim=0)
                }

            attention_mask = torch.stack(
                [torch.tensor([0] * (max(lengths) - len(x)) + [1] * len(x), dtype=torch.long) for x in input_ids]
            )
            input_ids = torch.stack(
                [torch.cat([torch.tensor([eos_token_id] * (max(lengths) - len(x)), dtype=torch.long), x], axis=0) for x in input_ids]
            )

            return {
                "input_ids": input_ids,
                "attention_mask": attention_mask
            }

    def adjust_logits_during_generation(self, logits: torch.FloatTensor, **kwargs) -> torch.FloatTensor:
        """
        Implement in subclasses of :class:`~transformers.PreTrainedModel` for custom behavior to adjust the logits in
        the generate method.
        """
        return logits

    def _prepare_input_ids_for_generation(
        self, bos_token_id: Optional[int], encoder_outputs: Optional[ModelOutput]
    ) -> torch.LongTensor:
        if self.config.is_encoder_decoder and encoder_outputs is not None:
            # make dummy input_ids with value -100, as a sanity check ensuring that they won't be used for encoding
            shape = encoder_outputs.last_hidden_state.size()[:-1]
            return torch.ones(shape, dtype=torch.long, device=self.device) * -100

        if bos_token_id is None:
            raise ValueError("`bos_token_id` has to be defined when no `input_ids` are provided.")
        return torch.ones((1, 1), dtype=torch.long, device=self.device) * bos_token_id

    def _prepare_attention_mask_for_generation(
        self, input_ids: torch.Tensor, pad_token_id: int, eos_token_id: int
    ) -> torch.LongTensor:
        is_pad_token_in_inputs_ids = (pad_token_id is not None) and (pad_token_id in input_ids)
        is_pad_token_not_equal_to_eos_token_id = (eos_token_id is None) or (
            (eos_token_id is not None) and (pad_token_id != eos_token_id)
        )
        if is_pad_token_in_inputs_ids and is_pad_token_not_equal_to_eos_token_id:
            return input_ids.ne(pad_token_id).long()
        return input_ids.new_ones(input_ids.shape, dtype=torch.long)

    def _prepare_encoder_decoder_kwargs_for_generation(
        self, input_ids: torch.LongTensor, model_kwargs
    ) -> Dict[str, Any]:
        if "encoder_outputs" not in model_kwargs:
            # retrieve encoder hidden states
            encoder = self.get_encoder()
            encoder_kwargs = {
                argument: value
                for argument, value in model_kwargs.items()
                if not (argument.startswith("decoder_") or argument.startswith("cross_attn"))
            }
            model_kwargs["encoder_outputs"]: ModelOutput = encoder(input_ids, return_dict=True, **encoder_kwargs)
        return model_kwargs

    def _prepare_decoder_input_ids_for_generation(
        self, input_ids: torch.LongTensor, decoder_start_token_id: int = None, bos_token_id: int = None
    ) -> torch.LongTensor:
        decoder_start_token_id = self._get_decoder_start_token_id(decoder_start_token_id, bos_token_id)
        decoder_input_ids = (
            torch.ones((input_ids.shape[0], 1), dtype=torch.long, device=input_ids.device) * decoder_start_token_id
        )
        return decoder_input_ids

    def _get_pad_token_id(self, pad_token_id: int = None, eos_token_id: int = None) -> int:
        if pad_token_id is None and eos_token_id is not None:
            logger.warning(f"Setting `pad_token_id` to `eos_token_id`:{eos_token_id} for open-end generation.")
            pad_token_id = eos_token_id
        return pad_token_id

    def _get_decoder_start_token_id(self, decoder_start_token_id: int = None, bos_token_id: int = None) -> int:
        decoder_start_token_id = (
            decoder_start_token_id if decoder_start_token_id is not None else self.config.decoder_start_token_id
        )
        bos_token_id = bos_token_id if bos_token_id is not None else self.config.bos_token_id

        if decoder_start_token_id is not None:
            return decoder_start_token_id
        elif (
            hasattr(self.config, "decoder")
            and hasattr(self.config.decoder, "decoder_start_token_id")
            and self.config.decoder.decoder_start_token_id is not None
        ):
            return self.config.decoder.decoder_start_token_id
        elif bos_token_id is not None:
            return bos_token_id
        elif (
            hasattr(self.config, "decoder")
            and hasattr(self.config.decoder, "bos_token_id")
            and self.config.decoder.bos_token_id is not None
        ):
            return self.config.decoder.bos_token_id
        raise ValueError(
            "`decoder_start_token_id` or `bos_token_id` has to be defined for encoder-decoder generation."
        )

    @staticmethod
    def _expand_inputs_for_generation(
        input_ids: torch.LongTensor,
        expand_size: int = 1,
        is_encoder_decoder: bool = False,
        attention_mask: torch.LongTensor = None,
        encoder_outputs: ModelOutput = None,
        **model_kwargs,
    ) -> Tuple[torch.LongTensor, Dict[str, Any]]:
        expanded_return_idx = (
            torch.arange(input_ids.shape[0]).view(-1, 1).repeat(1, expand_size).view(-1).to(input_ids.device)
        )
        input_ids = input_ids.index_select(0, expanded_return_idx)

        if "token_type_ids" in model_kwargs:
            token_type_ids = model_kwargs["token_type_ids"]
            model_kwargs["token_type_ids"] = token_type_ids.index_select(0, expanded_return_idx)

        if attention_mask is not None:
            model_kwargs["attention_mask"] = attention_mask.index_select(0, expanded_return_idx)

        if is_encoder_decoder:
            assert encoder_outputs is not None
            encoder_outputs["last_hidden_state"] = encoder_outputs.last_hidden_state.index_select(
                0, expanded_return_idx.to(encoder_outputs.last_hidden_state.device)
            )
            model_kwargs["encoder_outputs"] = encoder_outputs
        return input_ids, model_kwargs

    @staticmethod
    def _update_model_kwargs_for_generation(
        outputs: ModelOutput, model_kwargs: Dict[str, Any], 
        is_encoder_decoder: bool = False, 
        padding_tokens: Optional[torch.LongTensor] = None
    ) -> Dict[str, Any]:
        # print("TODO: _update_model_kwargs_for_generation still has to be adapted to handle padding_tokens (adjust position_ids, token_type_ids, attention_mask)")

        # update past
        if "past_key_values" in outputs:
            model_kwargs["past"] = outputs.past_key_values
        elif "mems" in outputs:
            model_kwargs["past"] = outputs.mems
        elif "past_buckets_states" in outputs:
            model_kwargs["past"] = outputs.past_buckets_states
        else:
            model_kwargs["past"] = None

        # update token_type_ids with last value
        if "token_type_ids" in model_kwargs:
            token_type_ids = model_kwargs["token_type_ids"]
            model_kwargs["token_type_ids"] = torch.cat([token_type_ids, token_type_ids[:, -1].unsqueeze(-1)], dim=-1)

        # update attention mask
        if not is_encoder_decoder:
            if "attention_mask" in model_kwargs:
                attention_mask = model_kwargs["attention_mask"]
                model_kwargs["attention_mask"] = torch.cat(
                    [attention_mask, attention_mask.new_ones((attention_mask.shape[0], 1))], dim=-1
                )

        return model_kwargs

    def _reorder_cache(self, past, beam_idx):
        raise NotImplementedError(
            f"Make sure that a `_reorder_cache` function is correctly implemented in {self.__class__.__module__} to enable beam search for {self.__class__}"
        )

    def _get_logits_warper(
        self, top_k: int = None, top_p: float = None, temperature: float = None, num_beams: int = None
    ) -> LogitsProcessorList:
        """
        This class returns a :obj:`~transformers.LogitsProcessorList` list object that contains all relevant
        :obj:`~transformers.LogitsWarper` instances used for multinomial sampling.
        """

        # init warp parameters
        top_k = top_k if top_k is not None else self.config.top_k
        top_p = top_p if top_p is not None else self.config.top_p
        temperature = temperature if temperature is not None else self.config.temperature
        # instantiate warpers list
        warpers = LogitsProcessorList()

        # the following idea is largely copied from this PR: https://github.com/huggingface/transformers/pull/5420/files
        # all samplers can be found in `generation_utils_samplers.py`
        if temperature is not None and temperature != 1.0:
            warpers.append(TemperatureLogitsWarper(temperature))
        if top_k is not None and top_k != 0:
            warpers.append(TopKLogitsWarper(top_k=top_k, min_tokens_to_keep=(2 if num_beams > 1 else 1)))
        if top_p is not None and top_p < 1.0:
            warpers.append(TopPLogitsWarper(top_p=top_p, min_tokens_to_keep=(2 if num_beams > 1 else 1)))
        return warpers

    def _get_logits_processor(
        self,
        repetition_penalty: float,
        no_repeat_ngram_size: int,
        encoder_no_repeat_ngram_size: int,
        encoder_input_ids: torch.LongTensor,
        bad_words_ids: List[List[int]],
        min_length: int,
        max_length: int,
        eos_token_id: int,
        forced_bos_token_id: int,
        forced_eos_token_id: int,
        prefix_allowed_tokens_fn: Callable[[int, torch.Tensor], List[int]],
        num_beams: int,
        num_beam_groups: int,
        diversity_penalty: float,
        remove_invalid_values: bool,
        additional_logits_processors: Optional[list],
    ) -> LogitsProcessorList:
        """
        This class returns a :obj:`~transformers.LogitsProcessorList` list object that contains all relevant
        :obj:`~transformers.LogitsProcessor` instances used to modify the scores of the language model head.
        """
        processors = AsyncLogitsProcessorList()

        # init warp parameters
        repetition_penalty = repetition_penalty if repetition_penalty is not None else self.config.repetition_penalty
        no_repeat_ngram_size = (
            no_repeat_ngram_size if no_repeat_ngram_size is not None else self.config.no_repeat_ngram_size
        )
        encoder_no_repeat_ngram_size = (
            encoder_no_repeat_ngram_size
            if encoder_no_repeat_ngram_size is not None
            else self.config.encoder_no_repeat_ngram_size
        )
        bad_words_ids = bad_words_ids if bad_words_ids is not None else self.config.bad_words_ids
        min_length = min_length if min_length is not None else self.config.min_length
        eos_token_id = eos_token_id if eos_token_id is not None else self.config.eos_token_id
        diversity_penalty = diversity_penalty if diversity_penalty is not None else self.config.diversity_penalty
        forced_bos_token_id = (
            forced_bos_token_id if forced_bos_token_id is not None else self.config.forced_bos_token_id
        )
        forced_eos_token_id = (
            forced_eos_token_id if forced_eos_token_id is not None else self.config.forced_eos_token_id
        )
        remove_invalid_values = (
            remove_invalid_values if remove_invalid_values is not None else self.config.remove_invalid_values
        )
        # instantiate processors list

        # the following idea is largely copied from this PR: https://github.com/huggingface/transformers/pull/5420/files
        # all samplers can be found in `generation_utils_samplers.py`
        if diversity_penalty is not None and diversity_penalty > 0.0:
            processors.append(
                HammingDiversityLogitsProcessor(
                    diversity_penalty=diversity_penalty, num_beams=num_beams, num_beam_groups=num_beam_groups
                )
            )
        if repetition_penalty is not None and repetition_penalty != 1.0:
            processors.append(RepetitionPenaltyLogitsProcessor(penalty=repetition_penalty))
        if no_repeat_ngram_size is not None and no_repeat_ngram_size > 0:
            processors.append(NoRepeatNGramLogitsProcessor(no_repeat_ngram_size))
        if encoder_no_repeat_ngram_size is not None and encoder_no_repeat_ngram_size > 0:
            if self.config.is_encoder_decoder:
                processors.append(EncoderNoRepeatNGramLogitsProcessor(encoder_no_repeat_ngram_size, encoder_input_ids))
            else:
                raise ValueError(
                    "It's impossible to use `encoder_no_repeat_ngram_size` with decoder-only architecture"
                )
        if bad_words_ids is not None:
            processors.append(NoBadWordsLogitsProcessor(bad_words_ids, eos_token_id))
        if min_length is not None and eos_token_id is not None and min_length > -1:
            processors.append(MinLengthLogitsProcessor(min_length, eos_token_id))
        if prefix_allowed_tokens_fn is not None:
            processors.append(PrefixConstrainedLogitsProcessor(prefix_allowed_tokens_fn, num_beams // num_beam_groups))
        if forced_bos_token_id is not None:
            processors.append(ForcedBOSTokenLogitsProcessor(forced_bos_token_id))
        if forced_eos_token_id is not None:
            processors.append(ForcedEOSTokenLogitsProcessor(max_length, forced_eos_token_id))
        if remove_invalid_values is True:
            processors.append(InfNanRemoveLogitsProcessor())

        processors += (additional_logits_processors if additional_logits_processors is not None else [])
        return processors

    async def logits(
        self,
        input_ids: torch.LongTensor,
        logits_mask: Optional[torch.LongTensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        temperature: Optional[float] = None,
        repetition_penalty=None,
        no_repeat_ngram_size=None,
        bad_words_ids=None,
        prefix_allowed_tokens_fn=None,
        diversity_penalty=None,
        remove_invalid_values=None,
        additional_logits_processors=None,
        min_tokens_to_keep: Optional[int] = None,
        additional_logits_processor_mask: Optional[torch.BoolTensor] = None,
        eos_token_id: Optional[int] = None,
        **model_kwargs,
    ) -> Tuple[torch.FloatTensor, torch.FloatTensor]:
        
        logits_processor = self._get_logits_processor(
            repetition_penalty=repetition_penalty,
            no_repeat_ngram_size=no_repeat_ngram_size,
            encoder_no_repeat_ngram_size=None,
            encoder_input_ids=None,
            bad_words_ids=bad_words_ids,
            min_length=None,
            max_length=None,
            eos_token_id=None,
            forced_bos_token_id=None,
            forced_eos_token_id=None,
            prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
            num_beams=None,
            num_beam_groups=None,
            diversity_penalty=diversity_penalty,
            remove_invalid_values=remove_invalid_values,
            additional_logits_processors=additional_logits_processors
        )

        assert min_tokens_to_keep is None or min_tokens_to_keep == 1 or min_tokens_to_keep == 2, "min_tokens_to_keep must be either 1,2 or None"
        # get probability distribution warper
        logits_warper = self._get_logits_warper(
            top_k=top_k, top_p=top_p, temperature=temperature, num_beams=2 if min_tokens_to_keep == 2 else 1
        )
        
        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )

        # prepare model inputs
        model_inputs = self.prepare_inputs_for_generation(input_ids, **model_kwargs, eos_token_id=eos_token_id)

        # forward pass to get next token
        outputs = await self(
            **model_inputs,
            return_dict=True,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
        )
        next_token_logits = outputs.logits[:, -1, :]
        raw_logits = next_token_logits.clone().detach()
        
        next_token_scores = await logits_processor(input_ids, next_token_logits, additional_logits_processor_mask=additional_logits_processor_mask)
        
        # apply additive logits mask
        if logits_mask is not None:
            assert additional_logits_processors is None, "additional_logits_processors and the additive logits_mask are expected to be mutually exclusive"
            tokenizer_range = logits_mask.size(-1)
            next_token_scores[:,:tokenizer_range] = next_token_scores[:,:tokenizer_range] + logits_mask
        
        next_token_scores = logits_warper(input_ids, next_token_scores)

        next_token_scores = next_token_scores - next_token_scores.logsumexp(-1, keepdim=True)
        raw_next_token_scores = raw_logits - raw_logits.logsumexp(-1, keepdim=True)

        return next_token_scores, raw_next_token_scores
    

    async def score(
        self,
        input_ids: torch.LongTensor,
        completion: torch.LongTensor,
        eos_token_id: Optional[int] = None,
        **model_kwargs,
    ) -> Tuple[torch.FloatTensor, torch.FloatTensor]:
        # prepare model inputs
        model_inputs = self.prepare_inputs_for_generation(input_ids, **model_kwargs, eos_token_id=eos_token_id)

        num_tokens_to_score = completion.size(-1)
        logits = []
        token_scores = []
        
        for i in range(num_tokens_to_score):
            # forward pass to get next token
            outputs = await self(
                **model_inputs,
                return_dict=True,
                output_attentions=False,
                output_hidden_states=False,
            )

            next_token_logits = outputs.logits[:, -1, :]
            logits.append(next_token_logits)
            next_token_logits = torch.log_softmax(next_token_logits, dim=-1)
            token_scores.append(next_token_logits.gather(-1, completion[:, i].unsqueeze(-1)))

            model_inputs["input_ids"] = torch.cat([model_inputs["input_ids"], completion[:, i].unsqueeze(-1)], dim=-1)

        return torch.cat(token_scores, dim=-1), torch.cat([l.unsqueeze(1) for l in logits], dim=1)

    async def unbiased_next_token_beam_scores(self, next_token_scores, beam_scores):
        # active_prompting_token_score = await logits_processor(input_ids, next_token_scores, filter_processors=["<class 'function'>"])
        unbiased_next_token_score = next_token_scores.clone()
        unbiased_next_token_score = unbiased_next_token_score + beam_scores[:, None].expand_as(unbiased_next_token_score)
        # unbiased_next_token_score = logits_warper(input_ids, unbiased_next_token_score)
        # unbiased_next_token_score = torch.zeros_like(next_token_scores) + beam_scores[:, None].expand_as(next_token_scores)

        return unbiased_next_token_score
