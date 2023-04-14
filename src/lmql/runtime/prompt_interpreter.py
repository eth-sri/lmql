import os
import re
import math
import asyncio
from dataclasses import dataclass
from lmql.ops import *
from lmql.runtime.decoder_head import DecoderHead
from lmql.runtime.output_writer import *
from lmql.runtime.rewriter import RewrittenInputIds
from lmql.runtime.model_registry import LMQLModelRegistry
from lmql.runtime.program_state import ProgramState
from lmql.runtime.backtracker import BacktrackerHeadMixin
from lmql.runtime.runtime import LMQLRuntime
from typing import Dict, Optional, Any

import numpy as np
from lmql.utils import nputil
from lmql.runtime.stats import Stats

import lmql.ops.token_set as token_set

from lmql.language.qstrings import qstring_to_stmts, TemplateVariable, DistributionVariable
from lmql.runtime.multi_head_interpretation import InterpretationHead, InterpreterCall, InterpreterHeadPool, InterpretationHeadDone

class DecodingError(Exception): ...
class FailedToDecodeVariable(Exception): ...

stats = Stats("interpreter")

def is_prefix_seq(seq1, seq2):
    num_matching = 0
    for v1, v2 in zip(seq1,seq2):
        if v1 == v2: num_matching += 1
        else: break
    return num_matching > 0

@dataclass
class LMQLResult:
    prompt: str
    variables: Dict[str, str]
    
    distribution_variable: Optional[str] = None
    distribution_values: Optional[str] = None

    @property
    def requires_distribution_postprocessing(self):
        return self.distribution_variable is not None

def copy(value):
    if value is None:
        return None
    elif type(value) is str:
        return value
    elif type(value) is list:
        return value.copy()
    else:
        assert False, "unhandled type in copy()"

class LMQLContextAPI:
    def __init__(self, program_variables, interpreter):
        self.program_variables: ProgramState = program_variables
        self.interpreter = interpreter

    async def json(self):
        return self.program_variables

    # LMQL runtime API

    def get_var(self, name):
        return self.program_variables.get_program_value(name)

    def query(self, qstring):
        return InterpreterCall(qstring, loc=None)

    def set_model(self, model_name):
        self.interpreter.set_model(model_name)

    def set_decoder(self, method, **kwargs):
        self.interpreter.set_decoder(method, **kwargs)

    def set_where_clause(self, where):
        self.interpreter.set_where_clause(where)

    def get_all_vars(self):
        return self.program_variables.variable_values.copy()

    def set_distribution(self, distribution_variable, values):
        self.interpreter.set_distribution(distribution_variable, values)

    def get_return_value(self):
        return LMQLResult(self.prompt, self.get_all_vars(), self.interpreter.distribution_variable, self.interpreter.distribution_values)

@dataclass
class HypothesisHeadState:
    valid: bool
    final: str
    program_state: ProgramState
    mask : Any
    stopping_phrases: List[List[int]]
    full_text : str
    where: Any
    trace: Any
    num_variables_decoded: int

class HypothesisHead(BacktrackerHeadMixin, LMQLContextAPI):
    def __init__(self, query_head, interpreter):
        super().__init__(ProgramState(runtime=interpreter), interpreter)

        self.head_index = 0
        self.query_head: InterpretationHead = query_head
        self.interpreter = interpreter
    
        self.last_seen_input_ids = None
        
        # prompt actions
        self.prompt = ""
        self.prompt_stmts = []

        # current template variable that is being decoded
        self.current_variable = None
        self.current_variable_offset = -1
        self.current_variable_scores = ()
        self.recurring_variable_counter = {}

        # track progress through the prompt
        self.num_variables_decoded = 0

        # current prompt segment that is actively fed to the model (only when active prompting is used)
        self.current_prompt = None

        # marks inactive heads which are only used for copies (will be removed from the pool in the next generation)
        self.prototype = False
        # index of the prototype head that this head was originally copied from
        self.prototype_head_index = -1

        # use self as query context (e.g. to get variables)
        query_head.context = self

        # num interpreted query calls
        self.num_queries = -1

        # masks collected during backtracking (only used by BacktrackerHeadMixin, when enabled)
        self.backtracker_masks = {}

        # keep track of last state after calling where_clause_logit_processor()
        self.last_state = None

    def copy(self) -> 'HypothesisHead':
        c = HypothesisHead(self.query_head.copy(), self.interpreter)
        c.head_index = -1
        c.program_variables = self.program_variables.copy()
        
        if self.last_seen_input_ids:
            c.last_seen_input_ids = self.last_seen_input_ids.copy()
        
        c.prompt = "" + self.prompt
        c.prompt_stmts = self.prompt_stmts.copy()

        c.current_variable = self.current_variable
        c.current_variable_scores = self.current_variable_scores
        c.current_prompt = copy(self.current_prompt)
        c.current_variable_offset = self.current_variable_offset

        c.num_variables_decoded = self.num_variables_decoded

        c.recurring_variable_counter = self.recurring_variable_counter.copy()
        c.num_queries = self.num_queries
        c.backtracker_masks = self.backtracker_masks.copy()

        c.last_state = self.last_state

        return c

    # hypothesis head API

    @property
    def num_last_seen_ids(self):
        if self.last_seen_input_ids is None:
            return 0
        else:
            return len(self.last_seen_input_ids)

    async def advance(self, active_prompting=False):
        if self.current_variable is not None:
            return
        if self.current_prompt is not None and active_prompting:
            return

        async def continue_for_more_prompt_stmts():
            if len(self.prompt_stmts) != 0: return

            if self.query_head.waiting:
                if self.query_head.done: return True
                await self.query_head.continue_()
            
            if not self.query_head.done:
                assert self.num_queries < self.query_head.num_calls, "query head {} is not advanced far enough: queries {} vs. head calls {}".format(self.query_head.id, self.num_queries, self.query_head.num_calls)

                self.num_queries = self.query_head.num_calls
                qstring = self.query_head.last_call_args[0]
                self.prompt_stmts = qstring_to_stmts(qstring)
        
        if self.query_head.waiting:
            await continue_for_more_prompt_stmts()

        while self.current_variable is None and self.current_prompt is None and not self.query_head.done:
            if len(self.prompt_stmts) == 0 and self.current_variable is None:
                if self.query_head.waiting:
                    await self.query_head.continue_()
                try:
                    await self.query_head.advance(self.prompt)
                except InterpretationHeadDone:
                    # rare case that occurs when self.query_head needs to be materialized first 
                    # and then turns out to be done already
                    break
                
                await continue_for_more_prompt_stmts()

                if self.query_head.done: break

            s = self.prompt_stmts[0]

            if type(s) is str:
                if not active_prompting:
                    self.prompt += s
                    self.prompt_stmts = self.prompt_stmts[1:]
                else:
                    self.current_prompt = s
                    self.prompt_stmts = self.prompt_stmts[1:]
                    return
            elif type(s) is TemplateVariable:
                self.current_variable = s.name
                # keep track of number of times a variable with this name has been decoded
                if self.current_variable not in self.recurring_variable_counter.keys():
                    self.recurring_variable_counter[s.name] = -1
                self.recurring_variable_counter[s.name] += 1
                
                self.prompt_stmts = self.prompt_stmts[1:]
                
                return
            elif type(s) is DistributionVariable:
                # distribution variables are skipped here, as the prompt interpreter will handle them
                # self.query_head must terminate after this part of the prompt (ensure by validation)
                distribution_var = s
                self.prompt_stmts = self.prompt_stmts[1:]

                assert len(self.prompt_stmts) == 0, "Distribution variables must be the last statement in a prompt"
            else:
                assert False, "prompt interpreter encountered unsupported prompt stmt of type {}".format(type(s))
    
    async def where_clause_logit_processor(self, head: DecoderHead):
        if self.current_variable_offset == -1:
            self.current_variable_offset = head.initial_prompt_offset - 1

        is_done = await self.advance()

        # print("where()", len(head.input_ids_without_padding), [(await head.detokenize(head.input_ids_without_padding))])

        # default results (if no where clause is run)
        valid = True
        is_final = "var"
        program_variables = self.program_variables.copy()
        trace = None
        logit_mask = None

        if is_done:
            mask = tset("eos")
            logit_mask = await head.translate_mask(mask, len(head.next_token_logits))
            stopping_phrases = []
        # follow_masking disabled
        elif self.current_variable is not None:
            with stats.timer("where_clause_logit_processor:follow_masking"):
                where = self.interpreter.where
                
                text = (await head.text(self.current_variable_offset, strip_padding=True))
                diff_text = (await head.text(max(self.current_variable_offset, self.num_last_seen_ids - 1), strip_padding=True))

                # current context
                program_variables: ProgramState = self.program_variables.copy()
                program_variables.set(self.current_variable, text, scores=self.current_variable_scores, diff=diff_text, montonicity="inc")

                # follow context
                follow_program_variables: ProgramState = self.program_variables.copy()
                follow_program_variables.set(self.current_variable, text + str(NextToken), scores=self.current_variable_scores, diff=diff_text, montonicity="inc")

                # digest token with where expr
                valid, is_final, trace = digest(where,
                    context=program_variables,
                    follow_context=follow_program_variables
                )

                stopping_conditions: List[StopAtOp] = execute_op_stops_at_only(where)
                stopping_phrases = {
                    "tokenized": [await s.stopping_phrase_tokenized(head.tokenizer_fn) for s in stopping_conditions if s.variable.name == self.current_variable],
                    "text": [s.stopping_phrase for s in stopping_conditions if s.variable.name == self.current_variable],
                }

                # check if follow_masking is disabled
                if not self.interpreter.configuration["follow_masking"]:
                    logit_mask = None
                    mask = "*"
                else:
                    # obtain where follow map
                    follow_map = where.follow_map if where is not None else None
                    # print(id(self), self.current_variable, [text], "mask", follow_map)
                    mask = create_mask(follow_map, valid, is_final)
                    logit_mask = await head.translate_mask(mask, len(head.next_token_logits))
        else:
            assert self.current_prompt is not None, f"error: where() is called but current variable and current prompt are None and query head is {self.query_head.done}"
            next_token = await self.get_next_prompt_token(head, pop=False)
            mask = tset("<prompt>")
            stopping_phrases = []
            logit_mask = await head.make_mask(next_token, vocab_size=len(head.next_token_logits))
        with stats.timer("where debugger out"):
            await self.debugger_output(head, valid, is_final, mask, stopping_phrases, program_variables, trace)

        # also include backtracking mask (only present if backtracking is enabled)
        logit_mask_backtracker = self.get_backtracker_mask(head)
        if logit_mask_backtracker is not None: 
            if logit_mask is not None:
                logit_mask = np.logical_and(logit_mask, np.logical_not(logit_mask_backtracker))
            else:
                logit_mask = np.logical_not(logit_mask_backtracker)

        # no mask, no logits processing
        if logit_mask is None:
            return head.next_token_logits

        # detect vocabulary mismatch
        if len(logit_mask) > len(head.next_token_logits):
            # sometimes the mask is longer than the logits (due to unused tokens)
            logit_mask = logit_mask[:len(head.next_token_logits)]
        else:
            assert len(head.next_token_logits) == len(logit_mask), "Vocabulary Mismatch: The LMQL client expects the served model to have a vocabulary dimension of {} but {} was found. Is the LMQL inference API running the correct model?". format(
                len(logit_mask), len(head.next_token_logits))

        # otherwise set disallowed logits to -inf (float min)
        head.next_token_logits[np.logical_not(logit_mask)] = np.finfo(np.float32).min

        return head.next_token_logits

    async def debugger_output(self, head: DecoderHead, valid, is_final, mask, stopping_phrases, program_variables, trace):
        where = self.interpreter.where

        # more expensive but needed when there are bugs in input_id rewriting
        full_text = await head.text(strip_padding=True, strip_eos=True)

        if self.current_prompt is not None:
            variable = f"<PROMPTING>"
            where = None
            trace = {}
            valid = True
            is_final = "var"
            program_variables = self.program_variables
        elif self.current_variable is not None:
            variable_recurrence = self.recurring_variable_counter[self.current_variable]
            variable = f"{self.current_variable}[{variable_recurrence}]"
        else:
            variable = "__done__"
            where = None
            trace = {}
            valid = True
            is_final = "fin"
            program_variables = self.program_variables
        
        self.interpreter.debugger_output(variable, head.seq_idx, full_text, where, trace, valid, is_final, mask, len(head.input_ids), program_variables)

        self.last_state = HypothesisHeadState(valid, is_final, program_variables.copy(), mask, stopping_phrases, full_text, where=where, trace=trace, num_variables_decoded=self.num_variables_decoded)

    async def json(self):
        if self.current_prompt is not None:
            variable = f"<PROMPTING>"
        elif self.current_variable is not None:
            variable_recurrence = self.recurring_variable_counter[self.current_variable]
            variable = f"{self.current_variable}[{variable_recurrence}]"
        else:
            variable = "__done__"

        if self.last_state is None:
            return {
                "head_index": self.head_index,
                "variable": variable, 
                # indicates dangeling hypothesis head without known state
                "unfinished": True
            }
        else:
            from lmql.utils.graph import CytoscapeGraphWriter

            def node_data(op):
                result = "-"
                if self.last_state.trace is not None and op in self.last_state.trace:
                    result = self.last_state.trace[op]

                follow_map = "-"
                if hasattr(op, "follow_map"):
                    follow_map = str(op.follow_map)
                return {
                    "result": result,
                    "follow_map": follow_map,
                    "repr": repr(op)
                }

            writer = CytoscapeGraphWriter(extra_data_provider=node_data)
            writer.write(self.last_state.where)
            
            last_state_dict = self.last_state.__dict__.copy()
            del last_state_dict["where"]
            del last_state_dict["trace"]

            last_state_dict["where"] = writer.graph.to_json(return_dict=True)

            return {
                "head_index": self.head_index,
                "variable": variable,
                # include information on valid, final, trace, mask, full_text
                **last_state_dict,
                "program_variables": self.program_variables
            }

    async def prepare_prompt(self, current_prompt, head: DecoderHead):
        if type(current_prompt) is list:
            return current_prompt
        else:
            assert type(current_prompt) is str
            return await head.tokenize(current_prompt)

    async def active_prompt(self, head: DecoderHead):
        assert "active_prompt is longer supported"

    async def get_next_prompt_token(self, head: DecoderHead, pop=True):
        if self.current_prompt is not None:
            self.current_prompt = await self.prepare_prompt(self.current_prompt, head)
            
            # if current prompt is empty, try again with next prompt statement (var or prompt)
            if len(self.current_prompt) == 0:
                self.current_prompt = None
                return await self.get_next_prompt_token(head)
            else:
                if not pop:
                    return self.current_prompt[0]
                next_token = self.current_prompt.pop(0)

                if len(self.current_prompt) == 0:
                    self.current_prompt = None
                    await self.advance(active_prompting=True)

                return next_token
        return None

    async def head_input_id_rewriter(self, head: DecoderHead):
        """
        Rewrite input IDs of this decoder head. 
        
        Returns None, if no rewrite is required.
        """
        if self.current_variable_offset == -1:
            self.current_variable_offset = head.initial_prompt_offset

        full_ids = head.input_ids_without_padding.tolist() + [head.next_token_id]
        self.last_seen_input_ids = full_ids

        if self.current_variable is not None:
            # keep track of scores per decoded variable
            if head.next_token_logprob is not None:
                self.current_variable_scores += (head.next_token_logprob,)
            else:
                self.current_variable_scores += (nputil.log_softmax(head.next_token_logits)[head.next_token_id],)

            # backtracking if enabled
            if self.interpreter.configuration["backtracking"] == True:
                # backtrack if required
                if not await self.backtracking_check_valid(head):
                    full_ids = head.input_ids_without_padding.tolist()[:-1]
                    self.last_seen_input_ids = full_ids
                    return RewrittenInputIds(appended_input_ids=None, strip_eos=-2)

        if head.is_at_eos() and self.current_variable is not None:
            text = (await head.text(strip_padding=True, offset=self.current_variable_offset))
            variable_value = text
            raw = variable_value
            # set raw variable value
            self.program_variables.set(self.current_variable, variable_value, scores=self.current_variable_scores[:-1], diff="", montonicity="fin")
            # apply postprocessing, if constraints specify it
            # - variable_value is the postprocessed, converted value (does not have to be a string)
            # - postprocessed_prompt is the string in the prompt that corresponds to the variable value
            variable_value, postprocessed_prompt = execute_postprocess(self.interpreter.where, self.current_variable, variable_value, context=self.program_variables)
            
            # set postprocessed variable value and program value
            self.program_variables.set(self.current_variable, postprocessed_prompt, program_value=variable_value, scores=self.current_variable_scores[:-1], diff="", montonicity="fin")
            self.current_variable = None
            
            self.num_variables_decoded += 1
            # update hypothesis head state to reflect that we have finished decoding a variable
            self.last_state.num_variables_decoded = self.num_variables_decoded
            
            self.current_variable_scores = ()

            # extend prompt
            prompt_length_before = len(self.prompt) # prompt without current variable
            old_prompt = self.prompt + text # prompt with current variable in raw form
            self.prompt += postprocessed_prompt # prompt with current variable in postprocessed form
            
            appended_value_prompt = self.prompt[prompt_length_before:]

            #  advance to next variable in prompt program (appends intermediate instructions to prompt)
            while self.current_variable is None and not self.query_head.done:
                await self.advance()

            # determines part of self.prompt that was appended by variable or program
            appended_program_prompt = self.prompt[prompt_length_before + len(appended_value_prompt):]

            if old_prompt != self.prompt or self.query_head.done:
                n_tokens_to_strip = len(self.last_seen_input_ids) - self.current_variable_offset
                value_ids, program_ids = await asyncio.gather(head.tokenize(appended_value_prompt), head.tokenize(appended_program_prompt))
                appended_ids = value_ids + program_ids
                value_offset = self.current_variable_offset + len(value_ids)
                
                # if query is finished, add eos token to appended IDs (indicates to decoder that this sequence/query has finished decoding)
                if self.query_head.done: 
                    appended_ids += [head.eos_token_id]
                
                self.last_seen_input_ids = head.input_ids_without_padding[:self.current_variable_offset].tolist() + appended_ids
                self.current_variable_offset = len(self.last_seen_input_ids)

                # appended input ids are now a full replacement for input ids
                return RewrittenInputIds(appended_input_ids=[head.eos_token_id] + self.last_seen_input_ids, strip_eos=-n_tokens_to_strip, value_offset=value_offset)
            else:
                # set last_seen_input_ids to current input_ids w/o eos token
                self.last_seen_input_ids = head.input_ids_without_padding.tolist()
                self.current_variable_offset = len(head.input_ids_without_padding)

                return RewrittenInputIds(appended_input_ids=None, strip_eos=True)
        return None

    def matches(self, decoder_head: DecoderHead, allow_none_match=False):
        if self.last_seen_input_ids is None and allow_none_match:
            # this should only happen for the root hypothesis
            return True
        def tolist(t):
            if type(t) is list: return t
            else: return t.tolist()
        
        # make sure that the decoder head is at the same variable as the hypothesis head
        decoder_variable = decoder_head.user_data.get("head", {}).get("variable", None)
        if self.current_variable is None:
            if decoder_variable != "__done__" and decoder_variable is not None:
                return False
        else:
            variable_recurrence = self.recurring_variable_counter[self.current_variable]
            head_variable = f"{self.current_variable}[{variable_recurrence}]"
            if decoder_variable != head_variable:
                return False
        
        # make sure the input_ids align
        return str(list(reversed(tolist(self.last_seen_input_ids)))) == str(list(reversed(tolist(decoder_head.input_ids_without_padding))))

class HypothesesBasedHeadPool:
    def __init__(self, intepreter, root_head):
        self.intepreter = intepreter

        self.initial_prompt = None

        self.root_head = root_head
        
        # self.num_generations = -1
        # self.previous_generation = -1
        # self.previous_generation_heads = []
        self.heads = {}
        self.heads_done = []
        self.head_bucket_mapping = {}

        self.head_ctr = -1

    def inc_head_ctr(self):
        self.head_ctr += 1
        return self.head_ctr

    async def prepare(self):
        await self.root_head.advance()
        self.initial_prompt = self.root_head.prompt

    def replace_head(self, head_to_replace, head_to_replace_with):
        if head_to_replace == self.root_head: 
            self.root_head = head_to_replace_with
        else:
            num_tokens = len(head_to_replace.last_seen_input_ids)
            i = self.heads[num_tokens].index(head_to_replace)
            self.heads[num_tokens][i] = head_to_replace_with

    async def get_head(self, decoder_head: DecoderHead, readonly=False) -> HypothesisHead:
        # determine set of matching heads
        num_tokens = len(decoder_head.input_ids_without_padding)
        candidate_heads = self.heads.get(num_tokens, [])
        matching_heads = [h for h in candidate_heads if h.matches(decoder_head)]

        if len(matching_heads) == 0:
            matching_heads = [self.root_head]

        if not (len(matching_heads) > 0):
            for depth, h in [(depth, h) for depth in self.heads for h in self.heads[depth]] + [(0, self.root_head)]:
                    if h.last_seen_input_ids is not None:
                        print("Head with (depth {}, head_index {}, prototype {}) '{}'".format(depth, h.head_index, h.prototype, [await decoder_head.detokenizer_fn(h.last_seen_input_ids)]))
                    else:
                        print("Head with (depth {}, head_index {}, prototype {}) '{}'".format(depth, h.head_index, h.prototype, "None"))

        assert len(matching_heads) > 0, "fatal: (head_index {}) no matching HypothesisHead for depth {} and decoder sequence {}"\
            .format(decoder_head.seq_idx, num_tokens, [await decoder_head.text()])
        
        # sort such that prototypes are in the back
        matching_heads = sorted(matching_heads, key=lambda h: 0 if not h.prototype else 1)

        # for read-only interaction we do not branch (e.g. where clause validation)
        if readonly: 
            # last_seen = matching_heads[0].last_seen_input_ids
            # if last_seen is not None:
            #     last_seen = [await decoder_head.detokenize(last_seen)]
            # print("matching head", [await decoder_head.text()], last_seen)
            return matching_heads[0]

        # find predecessor head
        previous_gen_head: HypothesisHead = matching_heads[0]
        if previous_gen_head.prototype:
            # create new head from prototype
            head = previous_gen_head.copy()
            head.head_index = self.inc_head_ctr()
            head.prototype = False
            head.prototype_head_index = previous_gen_head.prototype_head_index
        else:
            # use predecessor head and keep a copy as prototype for additional branches
            head = previous_gen_head
            prototype_to_keep = head.copy()
            prototype_to_keep.prototype = True
            prototype_to_keep.prototype_head_index = head.head_index
            prototype_to_keep.head_index = self.inc_head_ctr()
            self.replace_head(head, prototype_to_keep)

        self.add_head(head)

        return head

    def add_head(self, head: HypothesisHead):
        num_tokens = len(head.last_seen_input_ids) if head.last_seen_input_ids is not None else 0
        if num_tokens not in self.heads:
            self.heads[num_tokens] = []
        self.heads[num_tokens].append(head)
        self.head_bucket_mapping[head.head_index] = num_tokens

    def update_head(self, head: HypothesisHead):
        old_num_tokens = self.head_bucket_mapping[head.head_index]
        num_tokens = len(head.last_seen_input_ids) if head.last_seen_input_ids is not None else 0
        
        # remove heads with query_head.done 
        if head.query_head.done:
            self.heads[old_num_tokens].remove(head)
            self.heads_done.append(head)
            return

        if old_num_tokens != num_tokens:
            self.heads[old_num_tokens].remove(head)
            self.add_head(head)

    async def advance_generation_if_needed(self, generation, detokenizer=None):
        pass # we keep all the heads
        
        # if self.previous_generation == generation:
        #     return
        # else:
        #     self.num_generations += 1
            
        #     self.previous_generation = generation
        #     # only keep .last_seen_input_ids == None heads around for the first generation
        #     self.previous_generation_heads = [h for h in self.heads if h.last_seen_input_ids is not None or self.num_generations == 0]
        #     self.heads = []

        #     if detokenizer is not None:
        #         print("Generation {} ({} heads)".format(self.num_generations, len(self.previous_generation_heads)))
        #         for h in self.previous_generation_heads:
        #             print("Head with (head_index {}, prototype {}) '{}'".format(h.head_index, h.prototype, [await detokenizer(h.last_seen_input_ids) if h.last_seen_input_ids is not None else "None"]))

    async def run(self):
        if self.initial_prompt is None:
            await self.prepare()

        self.rewrite_cycle = 0

        async def where(head: DecoderHead, return_user_data=False):
            # # determine generation from rewrite cycle
            # if head.seq_idx == 0: self.rewrite_cycle += 1
            # generation = math.floor(self.rewrite_cycle / 2)
            
            # await self.advance_generation_if_needed(generation)

            with stats.timer("where"):
                interpreter_head = await self.get_head(head, readonly=True)

                if head.is_at_eos():
                    return head.next_token_logits
                logits = await interpreter_head.where_clause_logit_processor(head)

                if return_user_data:
                    return logits, {"head": await interpreter_head.json()}
                
                return logits
        
        async def rewriter(decoder_head: DecoderHead): 
            with stats.timer("rewrite"):
                head = await self.get_head(decoder_head)
                res = await head.head_input_id_rewriter(decoder_head)

                # update head storage location
                self.update_head(head)
                
                # keep track of the assigned interpreter head during further decoding
                head_data = await head.json()
                return RewrittenInputIds.with_user_data(res, "head", head_data)

        async def active_prompter(decoder_head): 
            # need to allow branching here because one where call might be followed by multiple active prompting calls 
            head = await self.get_head(decoder_head)
            return await head.active_prompt(decoder_head)

        with stats.timer("model.query"):
            query_result: Optional[List[DecoderHead]] = await self.intepreter.model.query(self.initial_prompt, where, rewriter, active_prompter)

        # collect query result
        head_result = []
        # if query() provides a set result heads use that
        if query_result is not None:
            for decoder_head in query_result:
                matching_done_interpreter_heads = [h for h in self.heads_done if h.matches(decoder_head)]
                if len(matching_done_interpreter_heads) > 0:
                    head_result += [h.query_head.result for h in matching_done_interpreter_heads]
                else:
                    print("warning: decoder designates head as done, but according to prompt interpreter it has not been completed yet:", await decoder_head.text(), "\n Did you specify a maximum length that has been exceeded?")
                    # print(decoder_head.user_data, self.heads)
        else:
            # otherwise use all heads that are .done
            for h in self.heads_done:
                if h.query_head.result is not None:
                    head_result.append(h.query_head.result)
        
        if len(head_result) == 0 and self.intepreter.distribution_variable is not None:
            print("warning: no heads were completed, but a distribution variable was specified. Cannot compute distribution.")

        if len(head_result) == 0:
            print("warning: the query has no valid result.")

        # print(stats)
        # print(VocabularyMatcher.instance().stats)

        if len(head_result) == 1:
            return head_result[0]
        else:
            return head_result

class PromptInterpreter(LMQLRuntime):
    def __init__(self, force_model=None):
        self.program_variables = ProgramState(runtime=self)
        self.where = None
        self.model = None

        self.force_model = force_model

        self.specified_decoder_args = {}

        self.preview = True
        self.output_writer: DebuggerOutputWriter = PrintingDebuggerOutputWriter()

        self.distribution_variable = None
        self.distribution_values = None

        # default configurations
        self.configuration = {
            "follow_masking": True,
            "backtracking": False,
            "stats": False,
            "prefers_compact_mask": False
        }

    def on_update_configuration(self, key):
        if key == "follow_masking" and not self.configuration["follow_masking"]:
            print("info: follow masking is disabled, where clause will be ignored")
        if key == "backtracking" and self.configuration["backtracking"]:
            print("info: running with backtracking enabled")
        if key == "prefers_compact_mask":
            print("info: running with prefers_compact_mask = {}".format(self.configuration["prefers_compact_mask"]))
            self.prefers_compact_mask = self.configuration["prefers_compact_mask"]

    def print_stats(self):
        if not self.configuration["stats"]:
            return

        client = self.model.served_model

        print("Queries: {}".format(client.num_queries))
        print("Tokens/Prompt: {}".format(client.consumed_tokens))
        print("generate() calls: {}".format(client.num_generate_calls))
        print("billable tokens: {}".format(client.billable_tokens))

    async def run(self, fct, *args, **kwargs):
        # intercept symbol table entry for input
        if "input" in kwargs.keys() and kwargs["input"] == input:
            kwargs["input"] = self.input
        
        root_head = HypothesisHead(InterpretationHead(fct, None, args = args, kwargs=kwargs), self)
        pool = HypothesesBasedHeadPool(self, root_head)
        return await pool.run()

    def debugger_output(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables):
        if self.output_writer is None: return
        self.output_writer.add_interpreter_head_state(variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables)

    def set_distribution(self, distribution_variable, values):
        self.distribution_variable = distribution_variable
        self.distribution_values = values

    async def input(self, *args):
        """Uses the output_writer input() implementation if available."""
        if hasattr(self.output_writer, "input"):
            return await self.output_writer.input(*args)
        else:
            return input(*args)

    def set_model(self, model):
        if self.force_model:
            # print("Forcing use of model {}, instead of {}.".format(self.force_model, model))
            model = self.force_model

        client = LMQLModelRegistry.get(model)

        # setup the VocabularyMatcher to use the concrete vocabulary of the model
        VocabularyMatcher.init(client.get_tokenizer())
        
        # for OpenAI models we optimize for compact logit masks
        if model.startswith("openai/"):
            self.prefers_compact_mask = True
            self.configuration["prefers_compact_mask"] = True

        self.model = client

    def set_decoder(self, method, **kwargs):
        assert self.model is not None, "Cannot set_decoder() before setting the model."
        self.specified_decoder_args = kwargs

        for key in self.configuration.keys():
            if key in kwargs:
                self.configuration[key] = kwargs[key]
                self.on_update_configuration(key)
        
        # pass output writer to model and decoder
        kwargs["output_writer"] = self.output_writer

        self.model.set_decoder(method, **kwargs)

    def set_where_clause(self, op):
        self.where = op