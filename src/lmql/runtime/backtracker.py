from dataclasses import dataclass

from lmql.ops import *
from lmql.runtime.decoder_head import DecoderHead
from lmql.runtime.rewriter import RewrittenInputIds
from lmql.runtime.model_registry import LMQLModelRegistry
from lmql.runtime.program_state import ProgramState

import lmql.ops.token_set as token_set

from lmql.language.qstrings import qstring_to_stmts, TemplateVariable, DistributionVariable
from lmql.runtime.multi_head_interpretation import InterpretationHead, InterpreterCall, InterpreterCall, InterpreterHeadPool

import numpy as np
from lmql.utils import nputil

def make_backtracker_mask(subtoken_id):
    mask = np.zeros(VocabularyMatcher.instance().vocab_size, dtype=np.bool_)
    mask[subtoken_id] = True
    return mask

class BacktrackerHeadMixin:
    def add_backtracker_mask(self, index, token_id):
        # backtracking masks (used to prevent backtracking into the same branch)
        if index not in self.backtracker_masks:
            self.backtracker_masks[index] = make_backtracker_mask(token_id)
        else:
            self.backtracker_masks[index] = np.logical_or(self.backtracker_masks[index], make_backtracker_mask(token_id))

        # remove backtracker masks that are no longer needed
        for k in self.backtracker_masks.keys():
            if k > index: del self.backtracker_masks[k]

    def get_backtracker_mask(self, head: DecoderHead):
        index = len(head.input_ids_without_padding)
        return self.backtracker_masks.get(index, None)

    async def backtracking_check_valid(self, head: DecoderHead):
        where = self.interpreter.where
            
        text = (await head.text(self.current_variable_offset, strip_padding=True))
        diff_text = (await head.text(max(self.current_variable_offset, self.num_last_seen_ids - 1), strip_padding=True))

        # current context
        program_variables: ProgramState = self.program_variables.copy()
        program_variables.set(self.current_variable, text, scores=self.current_variable_scores, diff=diff_text, montonicity="inc")

        # evaluate where clause
        valid, is_final, _ = digest(where, context=program_variables, follow_context=None, no_follow=True)

        if not valid and is_final == "fin":
            self.add_backtracker_mask(head.input_ids_without_padding.size(0) - 1, make_backtracker_mask(head.input_ids_without_padding[-1]))
            # self.add_backtracker_mask(head.input_ids_without_padding.size(0), make_backtracker_mask(head.input_ids_without_padding[-1]))
            return False
        return True