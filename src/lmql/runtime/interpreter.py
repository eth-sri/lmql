import asyncio
import inspect
from collections import namedtuple
from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Union, NamedTuple, Tuple, Set
import numpy as np

import re
import lmql.ops.ops as ops
import lmql.runtime.dclib as dc
from lmql.language.qstrings import (DistributionVariable, TemplateVariable,
                                    qstring_to_stmts)
from lmql.ops.follow_map import FollowMap
from lmql.ops.token_set import VocabularyMatcher, has_tail, tset
from lmql.ops.follow_map import fmap
from lmql.runtime.interrupt import interrupt
from lmql.runtime.model_registry import LMQLModelRegistry
from lmql.runtime.multi_head_interpretation import (InterpretationHead,
                                                    InterpretationHeadDone,
                                                    InterpreterCall)
from lmql.runtime.program_state import ProgramState
from lmql.runtime.stats import Stats
from lmql.runtime.tokenizer import LMQLTokenizer

from lmql.utils.nputil import replace_inf_nan_with_str
from lmql.runtime.interrupt import interrupt
from lmql.language.qstrings import qstring_to_stmts, TemplateVariable, DistributionVariable, unescape_qstring
from lmql.utils.nputil import replace_inf_nan_with_str

from lmql.ops.token_set import VocabularyMatcher, has_tail
from lmql.runtime.model_registry import LMQLModelRegistry
from lmql.models.model import model, LMQLModel

from lmql.ops.token_set import tset
import lmql.ops.ops as ops

class _DCLibDebugPrinter: pass
_DCLibDebugPrinter.printer = None

def set_dclib_debug_printer(printer):
    if hasattr(printer, "add_decoder_state"):
        _DCLibDebugPrinter.printer = printer

emoji_mapping = {}

@dataclass
class RewrittenInputIds:
    appended_input_ids: List[np.ndarray]
    strip_eos: bool = True
    user_data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None
    value_offset: Optional[int] = None
    
    # indicates whether or not this rewrite is a final rewrite (i.e. no further rewrites will be applied if it ends on eos)
    final: bool = True

    rewritten_seq_user_data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None

    @staticmethod
    def stack(results):
        return RewrittenInputIds(
            appended_input_ids=[r.appended_input_ids if r is not None else None for r in results],
            strip_eos=[r.strip_eos if r is not None else None for r in results],
            user_data=[r.user_data if r is not None else None for r in results],
            value_offset=[r.value_offset if r is not None else None for r in results],
            rewritten_seq_user_data=[r.rewritten_seq_user_data if r is not None else None for r in results],
            final=[r.final if r is not None else True for r in results]
        )

class advance: pass # used as symbol

class PromptState(NamedTuple):
    interpreter: 'PromptInterpreter'
    subinterpreters: Set['SubInterpreter']

    variable : str
    prompt : str
    
    stmt_buffer : List[Any]
    query_head : Any
    program_state : Any
    
    recurring_variable_counter : Dict[str, int]
    variable_offset : int

    # optional extra constraint only applicable to current context (inline where)
    constraints: Optional[ops.Node]

    # only set after processing where clause
    valid: Optional[bool]
    final: Optional[str] 
    mask : Optional[Any]
    stopping_phrases: Optional[Any]
    where: Optional[Any]
    tail: Optional[str]

    def __str__(self):
        return f"<PromptState '{self.variable}' '{[self.prompt]}'>"

    def updated(self, **updated):
        data_dict = self._asdict()
        data_dict.update(updated)
        return PromptState(**data_dict)
    
    def full_where_condition(self, interpreter):
        if interpreter.where is None:
            return self.constraints
        elif self.constraints is None:
            return interpreter.where
        else:
            return ops.AndOp([interpreter.where, self.constraints])

class LMQLContext:
    def __init__(self, interpreter, state, prompt):
        self.interpreter = interpreter
        
        if state:
            self.program_state: ProgramState = state.program_state
            self.state = state
            self.prompt = state.prompt
        else:
            self.program_state = ProgramState(prompt)
            self.state = None
            self.prompt = prompt

        self.program_state.runtime = interpreter

    async def json(self):
        return self.program_state

    # LMQL runtime API

    @property
    def num_calls(self):
        dcmodel = self.interpreter.dcmodel
        if hasattr(dcmodel, 'calls'):
            return dcmodel.calls - dcmodel.hits
        else:
            return 0

    async def get_var(self, name):
        return self.program_state.get_program_value(name)

    async def query(self, qstring, __locals, constraints=None):
        return InterpreterCall(qstring, __locals, constraints, loc=None)

    async def set_model(self, model_name):
        self.interpreter.set_model(model_name)

    async def set_decoder(self, method, **kwargs):
        self.interpreter.set_decoder(method, **kwargs)

    async def set_where_clause(self, where):
        self.interpreter.set_where_clause(where)

    async def get_context(self, *args):
        # prompt
        return self

    async def get_all_vars(self):
        return self.program_state.variable_program_values.copy()

    async def set_distribution(self, distribution_variable, values):
        self.interpreter.distribution_variable = distribution_variable
        self.interpreter.distribution_values = values

    async def get_return_value(self, *args):
        # for lmql.F functions, do not use LMQLResult and unpack single results
        if "is_f_function" in self.interpreter.extra_kwargs:
            result_values = await self.get_all_vars()
            if len(result_values) == 1:
                return list(result_values.values())[0]
            else:
                return result_values

        return LMQLResult(self.state.prompt, await self.get_all_vars(),self.interpreter.distribution_variable, self.interpreter.distribution_values)


@dataclass
class LMQLResult:
    prompt: str
    variables: Dict[str, str]
    
    distribution_variable: Optional[str] = None
    distribution_values: Optional[str] = None

    @property
    def requires_distribution_postprocessing(self):
        return self.distribution_variable is not None

@dataclass
class TokenMask:
    logits_mask: np.ndarray
    user_data: List[Any]

class PromptInterpreter:
    """
    The PromptInterpreter is the main entry point for an LMQL query. It handles program execution, 
    token masking and scripted interaction during query execution.
    """

    def __init__(self, context=None, force_model=None) -> None:
        # model-specific components
        self.model = force_model
        self.model_identifier = force_model
        self.tokenizer: LMQLTokenizer = None

        # decoder configuration
        self.decoder = None
        self.decoder_kwargs = None
        self.decoder_step = 0

        # extra interpreter flags passed via @lmql.query/@lmql.compiled_query
        self.extra_kwargs = {}

        # query program
        self.root_state = None

        # constraints
        self.where = None

        # distribution variable if any
        self.distribution_variable = None
        self.distribution_values = None

        # logging and debugger output
        self.output_writer = None
        self.prefers_compact_mask  = False
        
        # caching configuration
        self.caching = True
        self.cache_file = None
        self.show_speculative = False
        
        # key to use to store program statein decoding tree
        self.user_data_key = "head"

        self.eager_followmap_expansion = True
        
        # subinterpreters in case of inline queries
        self.subinterpreters = {}

        # decoder graph if decoder graph logging is enabled
        self.decoder_graph = None

        # context to determine model
        self.context = context

    def set_where_clause(self, where):
        self.where = where

    def set_extra_args(self, **kwargs):
        if "output_writer" in kwargs:
            self.output_writer = kwargs["output_writer"]
        # store remaining flags
        self.extra_kwargs.update(kwargs)

    def set_decoder(self, method, **kwargs):
        # remove compiler-level flags
        if "dump_compiled_code" in kwargs:
            kwargs.pop("dump_compiled_code")
        self.decoder_kwargs = kwargs
        self.decoder_kwargs["decoder"] = method

        if "backend" in kwargs:
            LMQLModelRegistry.backend_configuration = kwargs["backend"]

    def set_model(self, model_name):
        model_args = {}

        if type(model_name) is str:
            model_name = model(model_name)

        assert isinstance(model_name, LMQLModel), "Not a supported LMQL model '{}' of type '{}'".format(model_name, type(model_name))
        model_object = model_name

        if model_name.model is not None:
            model_object = model_name.model
            # if model_object is a type reference, instantiate it
            if callable(model_object):
                model_object = model_object()

            self.model_identifier = model_object.model_identifier
            self.model = model_object

            # setup the VocabularyMatcher to use the concrete vocabulary of the model
            VocabularyMatcher.init(self.model.get_tokenizer())

            return
        else:
            model_name = model_object.model_identifier
            model_args = model_object.kwargs

        if self.model is None:
            self.model = model_name
            self.model_identifier = model_name
        elif type(self.model_identifier) is not str:
            self.model_identifier = self.model.model_identifier

        client = LMQLModelRegistry.get(self.model, **model_args)

        if callable(client):
            client = client()

        # setup the VocabularyMatcher to use the concrete vocabulary of the model
        VocabularyMatcher.init(client.get_tokenizer())
        
        # for OpenAI models we optimize for compact logit masks
        if self.model_identifier.startswith("openai/"):
            self.prefers_compact_mask = True

        self.model = client

    async def advance(self, state: PromptState):
        if state.variable is not None:
            return state
        
        active_decoder_graph = dc.DecoderSequence.graph
        dc.DecoderSequence.graph = None
        
        variable = state.variable
        constraints = state.constraints
        
        stmt_buffer = state.stmt_buffer
        constraints_after_last_continue = constraints
        program_variables_after_last_continue = None
        prompt = state.prompt

        query_head = state.query_head

        async def continue_for_more_prompt_stmts():
            nonlocal stmt_buffer, query_head, constraints_after_last_continue, program_variables_after_last_continue

            if len(stmt_buffer) != 0: return
            
            if query_head.current_args is None:
                query_head = query_head.copy()
                assert query_head.fresh_copy, "query head must be fresh copy to avoid state sharing side effects"
                query_head.context = LMQLContext(self, state, prompt)
                await query_head.continue_()

            qstring = query_head.current_args[0]
            constraints_after_last_continue = query_head.current_args[2] if len(query_head.current_args) > 2 else None
            
            if len(query_head.current_args) > 2:
                program_variables_after_last_continue = query_head.current_args[1]
            
            stmt_buffer = qstring_to_stmts(qstring) + [advance]

            # return context used for last continue_
            return query_head.context
        
        # disable DecoderSequence.graph for the duration of executing the prompt

        try:
            while variable is None and query_head.result is None:
                if len(stmt_buffer) == 0 and variable is None:
                    await continue_for_more_prompt_stmts()

                s = stmt_buffer[0]

                if type(s) is str:
                    s = self.process_query_string(s)
                    prompt += s
                    stmt_buffer = stmt_buffer[1:]
                    constraints = None
                    
                    # keep latest prompt in transient state
                    state = state.updated(prompt=prompt)
                elif type(s) is TemplateVariable:
                    variable = s.name
                    constraints = constraints_after_last_continue
                    # keep track of number of times a variable with this name has been decoded
                    if variable not in state.recurring_variable_counter.keys():
                        state.recurring_variable_counter[s.name] = -1
                    state.recurring_variable_counter[s.name] += 1
                    
                    stmt_buffer = stmt_buffer[1:]
                    break
                elif type(s) is DistributionVariable:
                    # distribution variables are skipped here, as they are handled in a postprocessing step after returning an LMQL result
                    # self.query_head must terminate after this part of the prompt (ensure by validation)
                    stmt_buffer = stmt_buffer[1:]
                    assert len([s for s in stmt_buffer if s is not advance]) == 0, "Distribution variables must be the last statement in a prompt, but is {}".format(stmt_buffer)
                    # this will consume the set_distribution call
                elif s is advance:
                    query_head: InterpretationHead = query_head.copy()
                    query_head.context = LMQLContext(self, state, prompt)
                    assert query_head.fresh_copy, "query head must be fresh copy to avoid state sharing side effects"
                    await query_head.advance(None)
                    stmt_buffer = stmt_buffer[1:]
                else:
                    assert False, "prompt interpreter encountered unsupported prompt stmt of type {}: {}".format(type(s), s)
        except InterpretationHeadDone:
            pass

        # re-enable DecoderSequence.graph
        dc.DecoderSequence.graph = active_decoder_graph
        if self.output_writer is not None:
            self.output_writer.disable = False

        program_state = state.program_state.copy()
        program_state.python_scope = program_variables_after_last_continue or program_state.python_scope

        # merge named tuple with new stmt_buffer
        return state.updated(
            variable=variable,
            prompt=prompt,
            constraints=constraints,
            stmt_buffer=stmt_buffer,
            query_head=query_head,
            program_state=program_state
        )

    def process_query_string(self, s: str):
        if not ("turbo" in self.model_identifier or "gpt-4" in self.model_identifier):
            # replace all r"<lmql:(.*?)\/>" tags with ((\1))
            s = re.sub(r"<lmql:(.*?)\/>", r"((\1)):", s)
        s = unescape_qstring(s)
        return s

    def interpreter_state_user_data(self, state: PromptState):
        return {self.user_data_key: state}

    def interpreter_state_from_user_data(self, seq, noroot=False):
        if noroot:
            if seq.data(self.user_data_key) is None:
                return None
        state_dict = seq.data(self.user_data_key)
        if state_dict is None and not noroot:
            return self.root_state
        assert state_dict.interpreter is self, "error: interpreter state does not belong to this interpreter, {} vs. {} via {}".format(state_dict.interpreter, self, self.user_data_key)
        
        return state_dict

    async def where_for_sequence(self, s: dc.DecoderSequence, needs_masking, seqidx, return_follow_map=False, **kwargs):
        mask, logit_mask, state = await self.where_step_for_sequence(s, needs_masking, seqidx, return_follow_map=return_follow_map, **kwargs)

        # check for tail and prescore
        if hasattr(self.dcmodel, "prescore_tokens") and (not type(s) is dc.DeterministicDecoderSequence or len(s.next_ids) == 0):
            if has_tail(mask):
                tail_tokenized = self.tokenizer.tokenize(mask.tail, asbytes=True)
                await self.dcmodel.prescore_tokens(s, tail_tokenized, noscore=kwargs.get("noscore", False))

        return logit_mask, state

    async def where_step_for_sequence(self, s: dc.DecoderSequence, needs_masking, seqidx, return_follow_map=False, **kwargs):
        state = self.interpreter_state_from_user_data(s)
        
        if not needs_masking:
            return None, None, self.interpreter_state_user_data(state)

        is_done = state.query_head.result is not None

        # default results (if no where clause is run)
        valid = True
        is_final = "var"
        program_state = state.program_state.copy()
        trace = None
        logit_mask = None
        
        variable = state.variable
        variable_offset = state.variable_offset

        text = ""
        where = self.where

        if is_done:
            mask = tset("eos")
            logit_mask = mask.mask
            stopping_phrases = {"text": [], "tokenized": []}
            follow_trace = None
            
            follow_map = fmap(
                ("eos", (True, "fin")),
                ("*", (False, "fin"))
            )
        elif variable is not None:
            is_before = ":before" in variable
            if ":before" in variable:
                variable = variable.split(":before",1)[0]

            text = await s.text(variable_offset, pretty=False)
            diff_text = text[len(await s.text(variable_offset, limit=-1, pretty=False)):]

            # run applicable inline ops (sub interpreters)
            subvalid, subfollow, state = await self.subinterpreter_results(s, variable, text, diff_text, state, is_before, **kwargs)

            # current context
            program_state: ProgramState = state.program_state.copy()
            program_state.set(variable, text, scores=(), diff=diff_text, montonicity="inc")
            program_state.subinterpreter_results = subvalid
            program_state.prompt = state.prompt

            # follow context
            follow_program_state: ProgramState = state.program_state.copy()
            follow_program_state.set(variable, text + str(ops.NextToken), scores=(), diff=diff_text, montonicity="inc")
            follow_program_state.subinterpreter_results = subfollow
            follow_program_state.prompt = state.prompt

            # determine full where condition
            where = state.full_where_condition(self)

            # digest token with where expr
            valid, is_final, trace, follow_trace = ops.digest(where,
                context=program_state,
                follow_context=follow_program_state
            )

            # obtain where follow map
            follow_map = follow_trace[where] if where is not None else None
            # print(id(self), self.variable, [text], "mask", follow_map)
            mask = ops.create_mask(follow_map, valid, is_final)

            if mask == "*": 
                logit_mask = None
            else:
                logit_mask = mask.mask

            # check stopping conditions
            stopping_conditions: List[ops.StopAtOp] = ops.execute_op_stops_at_only(state.variable, where, trace)
            for sc in stopping_conditions:
                stop_trace = trace.copy()
                del stop_trace[sc]
                # check if stopping phrase applies in this step
                if ops.execute_op(sc, stop_trace, context=program_state, semantics="stop"):
                    mask = tset("eos")
                    logit_mask = mask.mask
                    follow_map = fmap(
                        ("eos", (True, "fin")),
                        ("*", (False, "fin"))
                    )
                    trace[sc] = (sc.stopping_phrase(trace), "stopped")
            stopping_phrases = {
                "text": [sc.stopping_phrase(trace) for sc in stopping_conditions if type(sc) is ops.StopBeforeOp],
                "tokenized": [self.tokenizer.tokenize(sc.stopping_phrase(trace), asbytes=True) 
                              for sc in stopping_conditions if type(sc) is ops.StopBeforeOp and sc.stopping_phrase(trace) is not None]
            }

        else:
            assert False, f"error: where() is called but current variable and current prompt are None and query head has result {state.query_head.result}"

        await self.debugger_output(state, s, valid, is_final, mask, stopping_phrases, program_state, trace, text, where)

        state = state.updated(
                        variable=variable,
                        valid=valid,
                        final=is_final,
                        mask=mask,
                        program_state=program_state,
                        stopping_phrases=stopping_phrases,
                        where=await self.where_graph_with_trace(where, trace, follow_trace)
        )

        if has_tail(mask):
            state = state.updated(tail = mask.tail)

        if return_follow_map:
            return mask, follow_map, self.interpreter_state_user_data(state)

        # truncate mask to remove LMQL specific token IDs
        logit_mask = self.tokenizer.truncate_to_model_dim(logit_mask)

        # no mask, no logits processing
        if logit_mask is None:
            return None, None, self.interpreter_state_user_data(state)
        
        # translate boolean mask to logit bias mask
        if len(mask) == 1:
            logit_mask = mask.mask.argmax()
        else:
            logit_mask = np.logical_not(logit_mask) * np.finfo(np.float32).min
        
        return mask, logit_mask, self.interpreter_state_user_data(state)

    async def where_graph_with_trace(self, where, trace, follow_trace):
        from lmql.utils.graph import CytoscapeGraphWriter

        def node_data(op):
            result = "-"
            follow_map = "-"
            if trace is not None and op in trace:
                result = trace[op]
            if follow_trace is not None and op in follow_trace:
                follow_map = follow_trace[op]

            return {
                "result": result,
                "follow_map": follow_map,
                "repr": repr(op)
            }

        writer = CytoscapeGraphWriter(extra_data_provider=node_data)
        writer.write(where)

        return writer.graph.to_json(return_dict=True)

    async def debugger_output(self, state: PromptState, s: dc.DecoderSequence, valid, is_final, mask, stopping_phrases, program_variables, trace, text, where):
        if self.output_writer is not None:
           await self.output_writer.add_interpreter_head_state(state.variable, 0, state.prompt + text, where, trace, valid, is_final, mask, len(s.input_ids), program_variables)

    async def where_processor(self, seqs, additional_logits_processor_mask, **kwargs):
        zipped_task_inputs = zip(seqs, additional_logits_processor_mask, range(len(seqs)))
        token_mask_tasks = [self.where_for_sequence(s, needs_masking, seqidx, **kwargs) for s,needs_masking, seqidx in zipped_task_inputs]
        results = [(mask, user_data) for mask, user_data in await asyncio.gather(*token_mask_tasks)]
        
        return TokenMask([r[0] for r in results], [r[1] for r in results])

    async def rewrite_for_sequence(self, seq: dc.DecoderSequence, needs_rewrite, assert_no_advance=False):
        if not needs_rewrite and not seq.is_done():
            return None
    
        # assert len([h for h in seq.user_data.keys() if "head" in h]) <= 2, "at max two heads are allowed in a sequence user_data"

        # obtain interpreter state from predecessor node
        state = self.interpreter_state_from_user_data(seq.predecessor, noroot=True)
        assert state is not None, "prompt interpreter state must be set in predecessor node"

        if state.tail is not None:
            rewritten_state = state.updated(tail=None)
            prompt_ids = seq.input_ids.tolist()
            tail_ids = self.tokenizer.tokenize(state.tail, asbytes=True)
            tail_ids = tail_ids[:-1]
            if len(tail_ids) > 1:
                updated_ids = prompt_ids + tail_ids[1:]

                return RewrittenInputIds(
                    appended_input_ids=updated_ids,
                    strip_eos=False,
                    value_offset=state.variable_offset + len(tail_ids),
                    user_data=self.interpreter_state_user_data(state),
                    rewritten_seq_user_data=self.interpreter_state_user_data(rewritten_state)
                )

        # first check for sub-interpreters
        subinterpreters: Set[SubInterpreter] = state.subinterpreters.copy()
        sub_results = []
        subrewrite_applied = False

        assert len(subinterpreters) <= 1

        user_data = seq.data() or {}

        for si in list(subinterpreters):
            if si.user_data_key not in seq.predecessor.user_data:
                subinterpreters.remove(si)
                continue

            result: RewrittenInputIds = await si.rewrite_for_sequence(seq, needs_rewrite, assert_no_advance=assert_no_advance)
            # print("sub rewrite result", result)
            user_data = dc.deepmerge(user_data, result.user_data)

            if result.appended_input_ids is not None or result.strip_eos != False:
                assert not subrewrite_applied, "subinterpreter must not apply rewrite if another subinterpreter already did"

                # apply rewrite
                sub_results.append(result)

                # remove subinterpreter if it rewrites to an eos token
                if result.appended_input_ids is not None and result.appended_input_ids[-1] == self.tokenizer.eos_token_id:
                    subinterpreters.remove(si)
                subrewrite_applied = True

        if len(sub_results) > 0:
            # make sure that changes to 'subinterpreters' are reflected in the state of the parent interpreter 
            # if a subtinterpreter has been removed
            state = state.updated(subinterpreters=subinterpreters)
            sub_results[0].user_data = dc.deepmerge(sub_results[0].user_data, self.interpreter_state_user_data(state))
            sub_results[0].rewritten_seq_user_data = dc.deepmerge(sub_results[0].rewritten_seq_user_data, self.interpreter_state_user_data(state))
            
            assert len(sub_results) == 1, "internal limitation: multiple concurrent subinterpreter rewrites are currently not supported. are you using more than one strategy constraint on the same variable?"

            sub_result = sub_results[0]
            sub_result.final = False
            return sub_result

        if seq.is_done() and state.variable is not None:
            program_state = state.program_state.copy()
            program_state.prompt = state.prompt
            variable = state.variable
            
            text = (await seq.text(offset=state.variable_offset, limit=-1, pretty=False))
            text_diff = text[len(await seq.text(state.variable_offset, limit=-2, pretty=False)):]
            
            variable_value = text
            # set raw variable value
            program_state.set(variable, variable_value, scores=(), diff=text_diff, montonicity="fin")

            where = state.full_where_condition(self)

            # apply postprocessing, if constraints specify it
            # - variable_value is the postprocessed, converted value (does not have to be a string)
            # - postprocessed_prompt is the string in the prompt that corresponds to the variable value
            variable_value, postprocessed_prompt = ops.execute_postprocess(where, variable, variable_value, context=program_state)

            if type(variable_value) is SubInterpreter:
                si = variable_value
                result_state = si.interpreter_state_from_user_data(seq)
                if result_state.query_head.result is not None:
                    variable_value = result_state.query_head.result
                    if type(variable_value) is LMQLResult:
                        postprocessed_prompt = variable_value.prompt
                    else:
                        postprocessed_prompt = str(result_state.query_head.result)

            # set postprocessed variable value and program value
            program_state.set(variable, postprocessed_prompt, program_value=variable_value, scores=(), diff="", montonicity="fin")

            # current variable is done
            variable = None
            prompt = state.prompt

            # extend prompt
            prompt_length_before = len(prompt) # prompt without current variable
            old_prompt = prompt + text # prompt with current variable in raw form
            prompt += postprocessed_prompt # prompt with current variable in postprocessed form
            
            appended_value_prompt = prompt[prompt_length_before:]

            #  advance to next variable in prompt program (appends intermediate instructions to prompt)
            assert not assert_no_advance, f"error: prompt interpreter tried to advance query program even though assert_no_advance was set"

            state = state.updated(variable=variable, prompt=prompt, program_state=program_state)
            
            while state.variable is None and state.query_head.result is None:
                state = await self.advance(state)
            reached_end = state.query_head.result is not None

            if reached_end:
                # make sure to store latest interpreter state in rewritten sequence when query is finished
                seq.user_data = self.interpreter_state_user_data(state)

            prompt = state.prompt

            # determines part of advanced_head.prompt that was appended by variable or program
            appended_program_prompt = prompt[prompt_length_before + len(appended_value_prompt):]

            variable_offset = state.variable_offset

            if old_prompt != prompt:
                n_tokens_to_strip = len(seq.input_ids) - variable_offset
                value_ids, program_ids = await asyncio.gather(*[self.tokenize(appended_value_prompt), self.tokenize(appended_program_prompt)])

                assert len(seq.input_ids) - n_tokens_to_strip == variable_offset, f"error: variable offset is not correct. expected {len(seq.input_ids) - n_tokens_to_strip} but got {state.variable_offset}"
                
                # if query is finished, add eos token to appended IDs (indicates to decoder that this sequence/query has finished decoding)
                if reached_end:
                    program_ids += [self.tokenizer.eos_token_id]
                
                # value_offset indicates to the decoder, that the first `value_offset` appended tokens are still the value 
                # of the variable, not deterministic tokens introduced by the prompt program
                appended_ids = value_ids + program_ids
                value_offset = state.variable_offset + len(value_ids)
                
                combined_new_ids = seq.input_ids[:-n_tokens_to_strip].tolist() + appended_ids

                res = []
                i = 0
                while i < len(combined_new_ids):
                    if type(combined_new_ids[i]) is bytes:
                        res += [combined_new_ids[i]]
                        i += 1
                    else:
                        j = i+1
                        while j < len(combined_new_ids) and type(combined_new_ids[j]) is not bytes:
                            j += 1
                        r = self.tokenizer.decode_bytes(combined_new_ids[i:j])
                        res += r
                        i = j
                combined_new_ids = np.array(res, dtype=np.bytes_)

                variable_offset = len(combined_new_ids)

                res = []
                i = 0
                while i < len(combined_new_ids):
                    if type(combined_new_ids[i]) is bytes or type(combined_new_ids[i]) is np.bytes_:
                        res += [combined_new_ids[i]]
                        i += 1
                    else:
                        j = i+1
                        while j < len(combined_new_ids) and type(combined_new_ids[j]) is not bytes:
                            j += 1
                        r = self.tokenizer.decode_bytes(combined_new_ids[i:j])
                        res += r
                        i = j
                combined_new_ids = np.array(res, dtype=np.bytes_)
                
                rewritten_state = state.updated(prompt=prompt, variable_offset=variable_offset, variable="__done__" if state.variable is None else state.variable + ":before")

                # appended input ids are now a full replacement for input ids
                return RewrittenInputIds(
                    appended_input_ids=combined_new_ids, 
                    strip_eos=-n_tokens_to_strip,
                    value_offset=value_offset,
                    user_data=self.interpreter_state_user_data(state),
                    rewritten_seq_user_data={
                        "backlink": seq.id,
                        **self.interpreter_state_user_data(rewritten_state)
                    }
                )
            else:
                # do nothing rewrite
                variable_offset = len(seq.input_ids) - 1
                state = state.updated(variable_offset=variable_offset, variable="__done__" if state.variable is None else state.variable)
                return RewrittenInputIds(
                    appended_input_ids=None, 
                    strip_eos=not reached_end, 
                    user_data=self.interpreter_state_user_data(state)
                )
        user_data[self.user_data_key] = state
        return RewrittenInputIds(appended_input_ids=None, strip_eos=False, user_data=user_data)

    async def tokenize(self, *args):
        # tokenize should be specific to the current model in use (infer from currently process
        # dc.seq, interpreter should not be tokenizer-specific)
        async def task():
            return self.tokenizer(*args)["input_ids"]
        t = asyncio.create_task(task())
        return (await t)
    
    async def rewrite_processor(self, seqs, mask_seq_to_rewrite):
        results = await asyncio.gather(*[self.rewrite_for_sequence(s, needs_rewrite) for s,needs_rewrite in zip(seqs, mask_seq_to_rewrite)])
        return RewrittenInputIds.stack(results)
    
    async def input(self, *args):
        """Uses the output_writer input() implementation if available."""
        if hasattr(self.output_writer, "input"):
            return await self.output_writer.input(*args)
        else:
            return input(*args)

    async def run(self, fct, *args, **kwargs):
        self.fct = fct

        # intercept symbol table entry for input
        if "input" in kwargs.keys() and kwargs["input"] == input:
            kwargs["input"] = self.input

        # prepare initial program state
        context = LMQLContext(self, None, "")
        query_head = InterpretationHead(fct, context, args, kwargs)
        self.root_state = PromptState(interpreter=self, subinterpreters={},
            variable=None, prompt="", stmt_buffer=[],
            query_head=query_head, program_state=context.program_state,
            constraints=None,
            recurring_variable_counter={}, variable_offset=0,
            valid=None, final=None, mask=None, 
            stopping_phrases=None, where=None,
            tail=None)
        self.root_state = await self.advance(self.root_state)

        # prepare dcmodel
        decoder_args = self.decoder_kwargs
        self.model.decoder_args = decoder_args
        self.dcmodel: dc.DcModel = self.model.get_dclib_model()

        # handle queries w/o any TemplateVariables
        if self.root_state.query_head.result is not None:
            return [self.root_state.query_head.result]

        # prepare tokenizer
        self.tokenizer = self.model.get_tokenizer()

        assert issubclass(type(self.dcmodel), dc.DcModel), "The provided dcmodel must be a subclass of DcModel"

        if "no_repeat_ngram_size" in decoder_args:
            print("warning: no_repeat_ngram_size is known to cause issues when used with constrained decoding, including non-termination.")

        # alternative mode where we only extract the prompt string
        return_prompt_string = self.extra_kwargs.pop("return_prompt_string", False)
        if return_prompt_string:
            return self.root_state.prompt

        # tokenize initial prompt
        prompt_ids = await self.tokenize(self.root_state.prompt)
        if self.dcmodel.bos_token_id is not None:
            prompt_ids = [self.dcmodel.bos_token_id] + prompt_ids
        
        prompt = self.tokenizer.tokenize(self.root_state.prompt, asbytes=True)
        n = len(prompt)
        
        # make sure that the initial prompt is not considered part of a variable
        self.root_state = self.root_state.updated(variable_offset=n)

        decoder_args = decoder_args.copy()

        # pass processor as decoder argument
        decoder_args["modern_logits_processor"] = self.where_processor
        
        # pass rewriter as decoder argument
        decoder_args["modern_rewriter"] = self.rewrite_processor

        if "__get_where__" in decoder_args:
            return self.where

        if "output_writer" in decoder_args:
            set_dclib_debug_printer(decoder_args["output_writer"])
        elif self.output_writer is not None:
            set_dclib_debug_printer(self.output_writer)

        if _DCLibDebugPrinter.printer is not None:
            if hasattr(_DCLibDebugPrinter.printer, "records_graph"):
                if _DCLibDebugPrinter.printer.records_graph:
                    dc.set_record_graph()
                    self.decoder_graph = dc.DecoderSequence.graph

        # get decoder function
        mode = decoder_args["decoder"].lower()
        # handle dynamically-set decoding (e.g. set via @lmql.query(decoder="beam", n=2))
        if mode == "__dynamic__":
            mode, extra_decoder_args = self.derive_decoder_args(self.extra_kwargs)
            decoder_args = {**decoder_args, **extra_decoder_args}
        decoder_fct = dc.get_decoder(mode)
        self.validate_args(decoder_args, decoder_fct)

        # alias max_length -> max_len
        if "max_length" in decoder_args:
            decoder_args["max_len"] = decoder_args["max_length"]
        if not "max_len" in decoder_args.keys():
            decoder_args["max_len"] = 2048
        
        # parse show_speculative argument
        if "show_speculative" in decoder_args.keys():
            self.show_speculative = decoder_args.pop("show_speculative")
            assert self.caching, "warning: show_speculative is only supported when caching is enabled."

        # parse cache argument
        if "cache" in decoder_args.keys():
            cache_value = decoder_args.pop("cache")
            if type(cache_value) is bool:
                if cache_value == False:
                    print("info: disabling model output caching")
                self.caching = cache_value
            elif type(cache_value) is str:
                self.caching = True
                self.cache_file = cache_value
            else:
                assert False, "Invalid value for 'cache' parameter. Expected either a boolean (to enable/disable) or a string (to enable with a disk-based cache file)"

        # setup dcmodel for use
        self.dcmodel.model_args = decoder_args
        if self.caching:
            self.dcmodel = dc.CachedDcModel(self.dcmodel, prompt_ids, cache_file=self.cache_file, show_speculative=self.show_speculative)
        decoder_args["dcmodel"] = self.dcmodel
        dc.set_truncation_threshold(self.dcmodel.truncation_threshold)

        assert len(prompt_ids) < decoder_args["max_len"], "The initial prompt already exceeds the provided max_len. Please increase the max_len or reduce the initial prompt (Initial prompt: '{}', max_len: {})".format(len(prompt_ids), decoder_args["max_len"])

        # set step budget at least to max_len
        step_budget = decoder_args.get("step_budget", max(1024, decoder_args.get("max_len", 1024)))
        
        async def debug_out(decoder_step):
            if PromptInterpreter.main != self:
                return
            if _DCLibDebugPrinter.printer is not None and dc.DecoderSequence.graph is not None:
                data = await dc.DecoderSequence.graph.json(diff=True)
                data = replace_inf_nan_with_str(data)
                _DCLibDebugPrinter.printer.add_decoder_state(data)
            self.dcmodel.report_stats(_DCLibDebugPrinter.printer, decoder_step)

        try:
            import time

            self.decoder_step = 0
            average_step_time = None
            start = time.time()
            async for _ in decoder_fct(prompt, **decoder_args):
                await debug_out(self.decoder_step)
                self.decoder_step += 1

                if step_budget is not None and self.decoder_step >= step_budget:
                    print("warning: step budget exceeded")
                    break

                if interrupt.check():
                    interrupt.clear()
                    raise InterruptedError("lmql.runtime.interrupt")
                
                average_step_time = (time.time() - start) if average_step_time is None else (average_step_time * 0.9 + (time.time() - start) * 0.1)

                if "performance_stats" in decoder_args:
                    if self.decoder_step % 10 == 0:
                        Stats.print_all()
                        print("step", self.decoder_step, "time", average_step_time)

                start = time.time()
            
            assert False, "decoder {} did not finish with dc.finish(), which means no result sequences were returned. \n\nThe reason for this may be a too small max_len value (max_len={}) ".format(decoder_args["decoder"], decoder_args["max_len"])
                
        except dc.FinishException as fe:
            # one last call to debug_out to get the final state
            await debug_out(self.decoder_step)
            # if dc.finish is used, the decoder sets the sequences it considers 
            # finished (return them to prompt interpreter)
            result_sequences = fe.result_sequences
            
            billable_tokens = 0
            for s in result_sequences:
                upper = len(s.input_ids)
                has_deterministic_tail = False
                while s.deterministic[upper-1] and upper >= 0:
                    upper -= 1
                    has_deterministic_tail = True
                # +1 for the eos token
                billable_tokens += upper + (1 if has_deterministic_tail else 0)
            
            results = []

            for i,s in enumerate(result_sequences):
                state = self.interpreter_state_from_user_data(s)
                if state.query_head.result is not None:
                    results.append(state.query_head.result)
                else:
                    state = await self.advance(state)
                    assert len(s.input_ids) < decoder_args["max_len"], "The decoder returned a sequence that exceeds the provided max_len (max_len={}, sequence length={}). To increase the max_len, please provide a corresponding max_len argument to the decoder function.".format(decoder_args["max_len"], len(s.input_ids))

                    assert state.query_head.result is not None, "decoder designates sequence {} as finished but the underyling query program has not produced a result. This is likekly a decoder bug. Decoder in use {}".format(await s.text(), decoder_args["decoder"])
                    results.append(state.query_head.result)
            
            # set decoder step +1, for all stats logging that happens in postprocessing
            self.decoder_step += 1

            return results

    def derive_decoder_args(self, extra_kwargs):
        # default is argmax
        decoder = extra_kwargs.get("decoder", "argmax")
        # if temperature is != 0, use 'sample'
        if extra_kwargs.get("temperature", 0.0) != 0.0:
            decoder = "sample"

        decoder_fct = dc.get_decoder(decoder)
        
        decoder_arg_names = inspect.getfullargspec(decoder_fct).args
        decoder_kwarg_names = inspect.getfullargspec(decoder_fct).kwonlyargs
        decoder_args = {}

        for a in decoder_arg_names + decoder_kwarg_names:
            if a in extra_kwargs.keys():
                decoder_args[a] = extra_kwargs[a]
        
        return decoder, decoder_args
    
    def validate_args(self, decoder_args, decoder_fct):
        INTERNAL_ARGS = ["decoder", "dcmodel", "modern_rewriter", "modern_logits_processor", "dclib_additional_logits_processor", 
                         "input_id_rewriter", "output_writer", "chunk_timeout", "chatty_openai", "distribution_batch_size", 
                         "openai_chunksize", "step_budget", "stats", "performance_stats", "cache", "show_speculative", 
                         "openai_nonstop", "chunksize"]

        # get all arg names and kwarg names of decoder function
        decoder_arg_names = inspect.getfullargspec(decoder_fct).args
        decoder_kwarg_names = inspect.getfullargspec(decoder_fct).kwonlyargs
        for k in decoder_args.keys():
            if k not in decoder_arg_names and k not in decoder_kwarg_names and k not in INTERNAL_ARGS:
                raise ValueError("Unknown decoder argument: {}".format(k))

    def print_stats(self):
        self.dcmodel.report_stats(self.output_writer, self.decoder_step)

    def subinterpreter(self, identifier, prompt, fct, captures):
        key = (identifier, prompt)

        if key in self.subinterpreters.keys():
            return self.subinterpreters[key]
        else:
            subinterpreter = SubInterpreter(fct, self, captures, model=self.model, model_identifier=self.model_identifier)
            
            # inherits interpreter attributes from parent
            subinterpreter.tokenizer = self.tokenizer
            subinterpreter.dcmodel = self.dcmodel
            
            self.subinterpreters[key] = subinterpreter
            
            return subinterpreter
        
    async def subinterpreter_results(self, s: dc.DecoderSequence, variable, text, diff_text, calling_state, is_before, **kwargs):
        where = calling_state.full_where_condition(self)
        inline_calls: List[ops.InlineCallOp] = [ic for ic in ops.InlineCallOp.collect(where) if ic.variable.name == variable]
        
        subfollow = {}
        subvalid = {}
        subinterpreters = []

        for ic in inline_calls:
            si = ic.subinterpreter(self, calling_state.prompt)
            if si is None: continue
            
            subinterpreters.append(si)
            
            # prepare subinterpreter if this is the first time it is used
            if si.root_state is None:
                await si.prepare(calling_state.variable_offset, calling_state.prompt)

            state = si.interpreter_state_from_user_data(s)
            # ids so far in subtinterpreter sequence space
            subinterpreter_prompt = calling_state.prompt + text
            # check if we need to first add the initial_subprompt_ids
            if len(si.root_state.prompt) > len(subinterpreter_prompt):
                remaining_suffix = si.root_state.prompt[len(subinterpreter_prompt):]
                # mask deterministically to produce si.root_state.prompt
                mask = ops.tset(remaining_suffix, prefix=True) # gives us first token of si.root_state.prompt + tail with remaining tokens

                s.user_data = dc.deepmerge(s.user_data, si.interpreter_state_user_data(state))
                s.user_data["set_by"] = "sub-where"

                subvalid[si] = state.valid
                subfollow[si] = ops.fmap(
                    (mask, ops.PredeterminedFinal(True, "var")),
                    ("*", ops.PredeterminedFinal(False, "fin"))
                )
            else:
                if len(si.root_state.prompt) == len(subinterpreter_prompt):
                    # set actual variable offset and store state back into current sequence
                    updated_offset_state = state.updated(variable_offset=len(s.input_ids))
                    s.user_data = dc.deepmerge(s.user_data, si.interpreter_state_user_data(updated_offset_state))

                follow_map, updated_user_data = await si.where_for_sequence(s, True, 0, return_follow_map=True, **kwargs)
                
                if updated_user_data is not None:
                    s.user_data = dc.deepmerge(s.user_data, updated_user_data)
                    s.user_data["set_by"] = "sub-where"
                
                valid = si.interpreter_state_from_user_data(s).valid
                
                subvalid[si] = valid

                # nothing to process if follow_map is None
                if follow_map is None:
                    subfollow[si] = None
                    continue

                # make sure final information is also propagated to the parent interpreter
                fixed_final_value_components = []
                for m, c in follow_map.components:
                    v, f = c
                    if type(f) is tuple:
                        f = f[0]
                    fixed_final_value_components.append((m, ops.PredeterminedFinal(v, f)))

                subfollow[si] = ops.fmap(*fixed_final_value_components)

        calling_state = calling_state.updated(subinterpreters=subinterpreters)
        
        return subvalid, subfollow, calling_state

class UserDataLayer:
    def __init__(self, sqs: List[dc.DecoderSequence], mappings):
        self.sqs: dc.DecoderSequence = sqs
        self.mappings = mappings
        self.prev_mappings = {}
    
    # enter and exit
    def __enter__(self):
        # for s in self.sqs:
        #     self.prev_mappings[s.id] = s.user_data
        #     s.user_data = self.mappings.get(s.id)
        pass

    def __exit__(self, type, value, traceback):
        # for s in self.sqs:
        #     self.mappings[s.id] = s.user_data
        #     s.user_data = self.prev_mappings.get(s.id)
        pass

PromptInterpreter.main = None

class SubInterpreter(PromptInterpreter):
    def __init__(self, fct, parent_interpreter: PromptInterpreter, captures: Dict[str, Any], model: str = None, model_identifier: str = None):
        super().__init__(context=parent_interpreter)
        self.query_fct = fct
        self.fct = fct.fct
        self.captures = captures

        # maps seq_id to this subinterpreters user_data layer
        self.user_data_mappings = {}

        self.user_data_key = "head[sub-" + str(id(self)) + "]"

        self.initial_subprompt_ids = None
        
        self.model = model
        self.model_identifier = model_identifier

    def set_model(self, model):
        # ignore set_model for subinterpreters
        pass

    def user_data_layer(self, *sqs):
        return UserDataLayer(sqs, self.user_data_mappings)

    async def prepare(self, parent_offset: int, prompt: str):
        # prepare initial program state
        context = LMQLContext(self, None, "")

        query_head = InterpretationHead(self.fct, context, args=[], kwargs=self.captures)
        self.root_state = PromptState(interpreter=self, subinterpreters=set(),
            variable=None, prompt=prompt, stmt_buffer=[],
            query_head=query_head, program_state=context.program_state,
            constraints=None,
            recurring_variable_counter={}, variable_offset=parent_offset,
            valid=None, final=None, mask=None, 
            stopping_phrases=None, where=None,
            tail=None)
        self.root_state = await self.advance(self.root_state)

        self.initial_subprompt_ids = await self.tokenize(self.root_state.prompt)
        self.n = len(self.initial_subprompt_ids)

        self.root_state = self.root_state.updated(variable_offset=self.n)

    def run(self, prompt, **kwargs):
        raise NotImplementedError("A SubInterpreter cannot be run directly. Please use the parent interpreter instead.")
