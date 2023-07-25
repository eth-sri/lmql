from tokenize import Token
from typing import Iterable, Tuple, List
from itertools import product

from lmql.ops.token_set import *
from lmql.ops.follow_map import *
from lmql.ops.node import *

from lmql.ops.inline_call import InlineCallOp
from lmql.ops.booleans import *
from lmql.ops.regex import Regex

lmql_operation_registry = {}

# @LMQLOp('function_name') decorator
def LMQLOp(name):
    def class_transformer(cls):
        # get full import path of cls
        cls_name = cls.__name__
        
        # if not in lmql.ops.ops, then use direct cls reference
        if cls.__module__ != "lmql.ops.ops":
            cls_name = cls

        if type(name) is list:
            for n in name:
                lmql_operation_registry[n] = cls_name
            return cls
        lmql_operation_registry[name] = cls_name
        return cls
    return class_transformer

def DynamicTypeDispatch(name, type_map):
    class TypeDispatchingNode(Node):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            self.delegate_args = args
            self.delegate_kwargs = kwargs
            self.delegate = None

        def get_handler(self, args):
            if self.delegate is not None:
                return self.delegate

            assert all(a is not None for a in args), "Cannot dispatch to handler with None arguments: {}".format(args)

            for signature, op in type_map:
                # fallback implementation
                if signature == "*": 
                    self.delegate = op(*self.delegate_args, **self.delegate_kwargs)
                    return self.delegate
                
                # check for matching signature
                is_match = True
                if type(signature) is tuple:
                    for arg, t in zip(args, signature):
                        is_match = is_match and isinstance(arg, t)
                else:
                    is_match = isinstance(args, signature)
                if is_match: 
                    self.delegate = op(*self.delegate_args, **self.delegate_kwargs)
                    return self.delegate
            raise NotImplementedError("error: no matching implemntation of {} for arguments of type {}".format(name, [type(arg) for arg in args]))

        def forward(self, *args, **kwargs):
            if any(a is None for a in args):
                return None
            return self.get_handler(args).forward(*args, **kwargs)
        
        def follow(self, *args, **kwargs):
            if any(a is None for a in args):
                return None
            return self.get_handler(args).follow(*args, **kwargs)
        
        def final(self, *args, **kwargs):
            if any(a is None for a in kwargs.get("operands")):
                return None
            return self.get_handler(kwargs.get("operands")).final(*args, **kwargs)
        
        def __str__(self):
            if self.delegate is not None:
                return str(self.delegate)
            return f"<{name}>"
        
        def __repr__(self):
            if self.delegate is not None:
                return repr(self.delegate)
            return f"<{name}>"
        
        def __nodelabel__(self):
            if self.delegate is not None:
                return self.delegate.__nodelabel__()
            return name

    return TypeDispatchingNode
@LMQLOp("SENTENCES")
class Sentences(Node):
    def forward(self, v, **kwargs):
        sentences = tuple(self.split(v, separator=["."]))
        return self.strip(sentences)
    
    def strip(self, sentences):
        if len(sentences) == 0:
            return sentences
        elif sentences[-1] == ():
            return tuple(sentences[:-1])
        else: 
            return tuple(sentences)

    def add_end(self, stc, end):
        if len(stc) == 0: return stc
        return stc + end

    def split(self, v, separator):
        result = ()
        
        current = ""
        for c in v:
            if c in separator:
                result += (current + c,)
                current = ""
            else:
                current += c
        if len(current) > 0:
            result += (current,)
        if len(result) == 0:
            return ("",)
        return result

    def follow(self, x, **kwargs):
        v = strip_next_token(x)
        has_next_token = v != x
        sentences = tuple(self.split(v, separator=["."]))

        if has_next_token: # continues with next token
            if len(sentences) > 0 and sentences[-1].endswith("."):
                return fmap(
                    ("eos", self.strip(sentences)),
                    ("*", sentences + (NextToken,))
                )
            else:
                return fmap(
                    ("eos", self.strip(sentences)),
                    ("*", tuple(sentences[:-1] + (sentences[-1] + NextToken,)))
                )
        else:
            return fmap(
                ("*", sentences)
            )

    def final(self, x, operands=None, result=None, **kwargs):
        return x[0]
    

@LMQLOp("INT")
class IntOp(Node):
    def forward(self, x, final=None, **kwargs):
        if x is None: return None
        if x == "": return None
        if final is not None and all(f == "fin" for f in final): return True

        # check int contains digits only
        if x.startswith(" "):
            x = x[1:]
        if not all([c in "0123456789" for c in x]):
            return False
        else:
            return True

    def follow(self, v, **kwargs):
        if v is None: return None
        
        has_next_token = v != strip_next_token(v)
        v = strip_next_token(v)

        context = kwargs.get("context", None)

        if context.runtime.prefers_compact_mask:
            number_tokens = tset("1","2","3","4","5","6","7","8","9","Ġ2","Ġ3","Ġ4","Ġ5","Ġ0","Ġ6","Ġ7","Ġ8","Ġ9","10","12","50","19","11","20","30","15","14","16","13","25","18","17","24","80","40","22","60","23","29","27","26","28","99","33","70","45","35","64","75","21","38","44","36","32","39","34","37","48","66","55","47","49","65","68","31","67","59","77","58","69","88","46","57","43","42","78","79","90","95","41","56","54","98","76","52","53","51","86","74","89","72","73","96","71","63","62","85","61","97","84","87","94","92","83","93","91","82","81", exact=True, name="number_tokens")
        else:
            number_tokens = tset("[ 1-9][0-9]*$", regex=True, name="full_number_tokens")
            number_cont_tokens = tset("[1-9][0-9]*$", regex=True, name="number_continuation_tokens")

        if not has_next_token:
            return fmap(
                ("eos", len(v.strip()) != 0),
                ("*", self.forward(v))
            )

        if not all([c.strip() in ",0123456789" for c in v]) and len(v.strip()) > 0:
            return fmap(
                ("*", False)
            )

        if "turbo" in context.runtime.model_identifier or "gpt-4" in context.runtime.model_identifier:
            if not all([c in "0123456789" for c in v]):
                return fmap(
                    ("*", False)
                )
            else:
                return fmap(
                    ("*", True)
                )

        if len(v) == 0:
            return fmap(
                (number_tokens, True),
                ("*", False)
            )
        else:
            if len(v.strip()) == 0:
                # do not allow empty strings
                return fmap(
                    (number_cont_tokens, True),
                    ("eos", False),
                    ("*", False)
                )

            # allow anything (either continue as number or stop by predicting any other 
            # token, which will be removed by the postprocessing)
            return fmap(
                ("*", True)
            )
        
    def postprocess_var(self, var_name):
        return var_name == self.predecessors[0].name

    def postprocess(self, operands, raw):
        raw = "".join([c for c in raw if c in "0123456789"])
        value = int(raw)
        return postprocessed_rewrite(str(value)), postprocessed_value(value)

    def postprocess_order(self, other, **kwargs):
        if isinstance(other, StopAtOp):
            return "after" # apply Int after StopAt
        else:
            return 0 # cannot be compared

    def final(self, x, operands=None, result=None, **kwargs):
        if result == False and x[0] == "inc":
            return "fin"
        return super().final(x, operands=operands, result=result, **kwargs)

@LMQLOp("TOKENS")
class TokensOp(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.depends_on_context = True

    def forward(self, x, context, **kwargs):
        if x is None: return None
        if x == "": return []

        return tuple(context.runtime.model.sync_tokenize(x))

    def follow(self, v, context=None, **kwargs):
        if v is None: return None
        contains_next_token = v != strip_next_token(v)

        if not contains_next_token:
            tokens = tuple(context.runtime.model.sync_tokenize(v))
            return tokens
        v = strip_next_token(v)
        tokens = tuple(context.runtime.model.sync_tokenize(v))

        return fmap(
            ("eos", tokens),
            ("*", (*tokens, NextToken))
        )

    def final(self, x, context, operands=None, result=None, **kwargs):
        return x[0]

@LMQLOp("WORDS")
class WordsOp(Node):
    def forward(self, x, **kwargs):
        if x is None: return None
        if x == "": return []
        # split on " " or "\n"
        x = x.replace(" ", " ")
        x = x.replace("\n", " ")
        x = x.replace("\u0120", " ")
        words = x.split(" ")

        return [w for w in words if w.strip() != ""]
    
    def follow(self, v, **kwargs):
        if v is None: return None
        contains_next_token = v != strip_next_token(v)
        words = self.forward(strip_next_token(v))

        components = [("*", (words + [NextToken]) if contains_next_token else words)]
        
        if len(words) > 0 and contains_next_token:
            # allow continuation sub-tokens
            continuation_tokens = tset("[^\u0120\n ].*", regex=True)
            # valid_continuations = union(tset("eos"), continuation_tokens)
            components = [
                ((continuation_tokens, (words[:-1] + [words[-1] + NextToken]))),
                ((tset("eos"), words))
            ] + components
        
        return fmap(
            *components
        )

    def final(self, x, operands=None, result=None, **kwargs):
        return x[0]

@LMQLOp("len")
class LenOp(Node):
    def forward(self, x, **kwargs):
        if x is None: return None
        if type(x) is list or type(x) is tuple:
            return len(x)
        if type(x) is not str: 
            x = str(x)
        return len(x)
    
    def follow(self, v, **kwargs):
        if v is None: return None
        if type(v) is list or type(v) is tuple:
            return len(v)
        else:
            v = str(v)
            assert type(v) is str, "len() can only be applied to strings, lists, or tuples"
            if NextToken not in v:
                return len(v)
            v = strip_next_token(v)
            
            len_masks = []
            for l,tmask in charlen_tsets().items():
                len_masks.append((tmask, len(v) + l))

            return fmap(*len_masks)

    def final(self, x, operands=None, result=None, **kwargs):
        return x[0]

class Lt(Node):
    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        return args[0] < args[1]
    
    def follow(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        return args[0] < args[1]

    def final(self, ops, operands=None, result=None, **kwargs):
        final_transition_indices = {"inc": 0, "dec": 1, "fin": 2, "var": 3}
        
        op1 = final_transition_indices[ops[0]]
        op2 = final_transition_indices[ops[1]]

        transition_table = [ # a < b
            # a "inc", "dec", "fin", "var"    # b
            [   "var", "fin", "fin", "var" ], # inc
            [   "var", "var", "var", "var" ], # dec
            [   "var", "fin", "fin", "var" ], # fin
            [   "var", "var", "var", "var" ], # var
        ]

        if result: 
            r = transition_table[op2][op1]
        else: 
            r = transition_table[op1][op2]
        
        return r

def Gt(preds): return Lt(list(reversed(preds)))

class EqOpGeneric(Node):
    def __init__(self, predecessors):
        super().__init__(predecessors)

    def forward(self, *args, **kwargs):
        return all([a == args[0] for a in args])

    def follow(self, *args, **kwargs):
        op1 = args[0]
        op2 = args[1]
        
        if op1 is None or op2 is None:
            return None
        
        
        if is_next_token(op1):
            if is_next_token(op2): 
                return fmap(
                    ("*", True)
                )
            else:
                return InOpStrInSet([]).follow(op1, [op2])
        if is_next_token(op2):
            if is_next_token(op1): 
                return fmap(
                    ("*", True)
                )
            else:
                return InOpStrInSet([]).follow(op2, [op1])

        if type(op1) is str or type(op2) is str:
            op_shorter = op1 if len(strip_next_token(op1)) < len(strip_next_token(op2)) else op2
            op_longer = op1 if len(strip_next_token(op1)) > len(strip_next_token(op2)) else op2

            if strip_next_token(op_longer) == op_longer and strip_next_token(op_shorter) != op_shorter:
                return InOpStrInSet([]).follow(op_shorter, [op_longer])

        return all([a == args[0] for a in args])

    def final(self, operand_final, operands=None, result=None, **kwargs):
        if not all(type(o) is str for o in operands):
            return super().final(operand_final, operands=operands, result=result, **kwargs)

        if result: # if equal, then fin iff all operands are fin
            return super().final(operand_final, operands=operands, result=result, **kwargs)
        
        if all([o == "fin" for o in operands]):
            return "fin"

        # result is False
        
        # determine longest, fixed prefix of final value
        fixed_value = None
        for o, of in zip(operands, operand_final):
            if of == "fin":
                if fixed_value is None:
                    fixed_value = o
                else:
                    if len(fixed_value) < len(o):
                        fixed_value = o
            elif of == "inc":
                if fixed_value is None: 
                    fixed_value = o
                else:
                    if len(fixed_value) < len(o):
                        fixed_value = o
            elif of == "var":
                continue
        
        # check that each operand is a prefix of the fixed_value
        for o, of in zip(operands, operand_final):
            if of == "fin":
                if fixed_value != o: return "fin"
            elif of == "inc":
                if not fixed_value.startswith(o): return "fin"
            else: # of == "var":
                continue
        
        return super().final(operand_final, operands=operands, result=result, **kwargs)

class EqOpInt(Node):
    def __init__(self, predecessors):
        super().__init__(predecessors)

    def forward(self, *args, **kwargs):
        return all([a == args[0] for a in args])

    def follow(self, *args, **kwargs):
        op1 = args[0]
        op2 = args[1]
        
        if op1 is None or op2 is None:
            return None
        
        return op1 == op2

    def final(self, operand_final, operands=None, result=None, **kwargs):
        op1f = operand_final[0]
        op1 = operands[0]
        op2f = operand_final[1]
        op2 = operands[1]

        if op1f == "fin" and op1 <= op2 and (op2f in ["fin", "inc"]):
            return "fin"
        if op2f == "fin" and op2 <= op1 and (op1f in ["fin", "inc"]):
            return "fin"

        # default behavior
        if all([a == "fin" for a in operand_final]):
            return "fin"
        
        return "var"

EqOp = DynamicTypeDispatch("EqOp", (
    ((int, int), EqOpInt),
    ("*", EqOpGeneric),
))

class SelectOp(Node):
    def forward(self, *args, **kwargs):
        if len(args[0]) <= args[1]:
            return None
        return args[0][args[1]]

    def follow(self, *args, **kwargs):
        l = args[0]
        idx = args[1]

        if l is None and idx is None:
            return None
        else:
            if l is not None and len(l) == idx + 1:
                return fmap(
                    ("eos", None),
                    ("*", l[idx])
                )
            else:
                return None

    def final(self, ops, operands, result, **kwargs):
        l = ops[0]
        idx = ops[1]

        if idx != "fin": return "var"

        if l == "fin": 
            return "fin"
        if result is not None and (l == "fin" or l == "inc"):
            return "fin"
        else: return "var"

class RawValueOp(Node):
    def __init__(self, args):
        super().__init__([])
        
        value, final = args
        self.value = value
        self.final_value = final

    def forward(self, **kwargs):
        return self.value

    def follow(self, **kwargs):
        return fmap(
            ("*", self.value)
        )

    def final(self, args, operands=None, result=None, **kwargs):
        return self.final_value

def matching_phrases_suffixes(x, allowed_phrases, allow_full_matches=False):
    x = strip_next_token(x)

    for phrase in allowed_phrases:
        if not phrase.startswith(x):
            continue
        if len(phrase) > len(x):
            yield phrase[len(x):]
        else:
            if allow_full_matches: 
                yield ""

class InOpStrInStr(Node):
    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None

        return args[0] in args[1]

    def follow(self, *args, **kwargs):
        op1 = strip_next_token(args[0])
        op1_generating = args[0] != op1
        op2 = strip_next_token(args[1])
        op2_generating = args[1] != op2

        assert not op1_generating, "InOpStrInStr: left-hand side operand must not be generating"

        # if op2 is finished, then the result is fixed
        if not op2_generating: return op1 in op2
        
        # if op1 already contained
        if op1 in op2: 
            return True

        # op1 is not contained in op2, so check for partial overlap with suffixes of op2
        overlap = 0
        for i in range(len(op1)):
            if op2[-i:] == op1[:i]:
                overlap = i
        suffix = op1[overlap:]
        suffix = suffix.replace(".", r"\.").replace("*", r"\*")

        allowed_subtokens = tset(f".*{suffix}.*", regex=True)

        return fmap(
            (allowed_subtokens, True),
            (setminus("*", allowed_subtokens), False)
        )

    def final(self, op_final, operands=None, result=None, **kwargs):
        if not result:
            return super().final(op_final, result=result, **kwargs)
        if op_final[1] == "inc" and op_final[0] == "fin":
            return "fin"
        return super().final(op_final, result=result, **kwargs)

class InOpStrInSet(Node):
    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        
        x = args[0]
        allowed_phrases = args[1]
        
        if x is None: 
            return None

        for _ in matching_phrases_suffixes(x, allowed_phrases, allow_full_matches=True):
            # any match is enough
            return True
        
        return False

    def follow(self, *args, **kwargs):
        if any([a is None for a in args]): return None

        x = args[0]
        allowed_phrases = args[1]

        suffixes = list(matching_phrases_suffixes(x, allowed_phrases, allow_full_matches=True))
        num_full_matches = len([s for s in suffixes if s == ""])
        suffixes = [s for s in suffixes if s != ""]
        
        if len(suffixes) == 0:
            if num_full_matches > 0 and not x.endswith(NextToken):
                return True
            return False
        else:
            full_remainders = [s + "$" for s in suffixes]
            if num_full_matches > 0: full_remainders.append("eos")

            return fmap(
                (tset(*full_remainders), True),
                (tset(*suffixes, prefix=True), PredeterminedFinal(False, "var")),
                ("*", PredeterminedFinal(False, "fin"))
            )

    def final(self, args, operands=None, result=None, **kwargs):
        x_final = args[0]

        if result is None:
            return "var"
        elif result == False:
            if x_final == "inc" or x_final == "fin":
                return "fin"
            return "var"
        else: # result == True
            if x_final == "fin":
                return "fin"
            return "var"

InOp = DynamicTypeDispatch("InOp", (
    ((str, str), InOpStrInStr),
    ("*", InOpStrInSet),
))

def seq_starts_with(seq1, seq2):
    num_matching = sum([1 if i1 == i2 else 0 for i1,i2 in zip(seq1, seq2)])
    return num_matching == len(seq2)

def remainder(seq: str, phrase: str):
    overlap = 0
    for i in range(len(phrase)):
        if seq[-i:] == phrase[:i]:
            overlap = i

    if overlap == 0: return None
    else: return phrase[i:]

@LMQLOp("REGEX")
class RegexOp(Node):
    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        x = args[0]
        ex = args[1]
        assert isinstance(ex, str)
        return Regex(ex).fullmatch(x)
    
    def follow(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        x = args[0]
        ex = args[1]
        assert isinstance(ex, str)
        
        if x == strip_next_token(x):
            return fmap(
                ("*", Regex(ex).fullmatch(x))
            )

        r = Regex(ex)
        rd = r.d(strip_next_token(x)) # take derivative
        print(f"r={r.pattern} x={strip_next_token(x)} --> {rd.pattern if rd is not None else '[no drivative]'}")
        if rd is None:
            return False 
        elif rd.is_empty(): # derivative is empty -> full match; therefore we must end
            return fmap(
                ("eos", True)
            )
        else: # only permit tokens form the regex derivative
            return fmap(
                (tset(rd.pattern, regex=True, prefix=True), True),
                #('*', False)
            )

    def final(self, ops_final, result=None, operands=None, **kwargs):
        if ops_final[0] == "fin": return "fin"
        else: return "var"

@LMQLOp("STARTS_WITH")
class StartsWithOp(Node):
    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        
        x = args[0]
        allowed_phrases = args[1]
        if isinstance(args[1], str): allowed_phrases = [allowed_phrases]

        for phrase in allowed_phrases:
            if x.startswith(phrase):
                return True

        return False

    def follow(self, *args, **kwargs):
        if any([a is None for a in args]): return None

        x = args[0]
        allowed_phrases = args[1]
        if isinstance(args[1], str): allowed_phrases = [allowed_phrases]

        # if there is any full match, then the result is True
        if any(strip_next_token(x).startswith(phrase) for phrase in allowed_phrases):
            return True

        # otherwise check for partial matches with the allowed phrases
        suffixes = list(matching_phrases_suffixes(x, allowed_phrases))

        if len(suffixes) == 0:
            return False
        else:
            return fmap(
                (tset(*suffixes), True),
                (ntset(*suffixes), False)
            )

    def final(self, ops_final, result=None, operands=None, **kwargs):
        op1 = ops_final[0]
        op2 = ops_final[1]

        if op1 == "inc" and op2 == "fin":
            if len(operands[0]) == 0 and not result:
                return "var"
            return "fin"
        
        return super().final(ops_final, **kwargs)
@LMQLOp(["STOPS_AT", "stops_at"])
class StopAtOp(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def execute_predecessors(self, trace, context):
        var_op: Var = self.predecessors[0]
        assert type(var_op) is Var, "The first argument of STOPS_AT must be a direct reference to a template variable."
        assert type(self.predecessors[1]) is str or type(self.predecessors[1]) is Var, "The second argument of STOPS_AT must be a string literal, but is {}.".format(type(self.predecessors[1]))
        var_op.diff_aware_read = True
        return super().execute_predecessors(trace, context)
    
    @property
    def variable(self):
        return self.predecessors[0]

    def forward(self, *args, final, **kwargs):
        return True

    def follow(self, *args, previous_result=None, **kwargs):
        return fmap(("*", True))

    def final(self, ops_final, operands, result, **kwargs):
        return "var"

    def stop(self, *args, final, **kwargs):
        if any([a is None for a in args]): return None

        if all([a == "fin" for a in final]): return False

        op1, op1_diff = args[0]
        op2 = args[1]

        if op1 is None: return False
        if op1_diff is None: op1_diff = ""


        matched_phrase_index = op1.rfind(op2)
        match_only_with_diff = op2 in op1 and matched_phrase_index >= len(op1) - len(op1_diff)

        return match_only_with_diff or op1.endswith(op2)

    def stopping_phrase(self, trace):
        if type(self.predecessors[1]) is Node:
            return trace[self.predecessors[1]]
        if type(self.predecessors[1]) is str:
            return self.predecessors[1]

    def postprocess_var(self, var_name):
        return var_name == self.predecessors[0].name

    def postprocess(self, operands, value):
        if value != operands[0][0]:
            return value
        value_diff: str = operands[0][1]
        stopping_phrase = operands[1]

        # find earliest match of stopping phrase in value_diff
        matched_phrase_index = value.rfind(stopping_phrase)
        next_matched_phrase_index = value.rfind(stopping_phrase, 0, matched_phrase_index)
        while next_matched_phrase_index != -1 and next_matched_phrase_index >= len(value) - len(value_diff):
            matched_phrase_index = next_matched_phrase_index
            next_matched_phrase_index = value.rfind(stopping_phrase, 0, matched_phrase_index)

        if matched_phrase_index + len(stopping_phrase) <= len(value) - len(value_diff):
            return None

        if matched_phrase_index != -1:
            value = value[:matched_phrase_index + len(stopping_phrase)]

        return postprocessed_rewrite(value), postprocessed_value(value)
    
    def postprocess_order(self, other, operands, other_inputs, **kwargs):
        if type(other) is IntOp:
            return "before"
        if isinstance(other, StopAtOp):
            value, value_diff = operands[0]
            op2 = operands[1]
            assert value == other_inputs[0][0], "internal error: comparing postprocess_order with two StopAtOps with different values (do they refer to different variables) {}".format((value, other_inputs[0]))
            matched_phrase_index = value.rfind(op2)
            other_matched_phrase_index = other_inputs[0][0].rfind(other_inputs[1])
            if matched_phrase_index == -1:
                return "before" # this operator does not match, so order does not matter
            if other_matched_phrase_index == -1:
                return "after" # other operator does not match, so order does not matter
            if matched_phrase_index < other_matched_phrase_index:
                return "before"
            else:
                return "after"
        
        return 0 # other constraints cannot be compared

@LMQLOp(["STOPS_BEFORE", "stops_before"])
class StopBeforeOp(StopAtOp):
    def postprocess(self, operands, value):
        value: str = operands[0][0]
        value_diff: str = operands[0][1]
        stopping_phrase = operands[1]

        # find earliest match of stopping phrase in value_diff
        matched_phrase_index = value.rfind(stopping_phrase)
        next_matched_phrase_index = value.rfind(stopping_phrase, 0, matched_phrase_index)
        while next_matched_phrase_index != -1 and next_matched_phrase_index >= len(value) - len(value_diff):
            matched_phrase_index = next_matched_phrase_index
            next_matched_phrase_index = value.rfind(stopping_phrase, 0, matched_phrase_index)

        if matched_phrase_index + len(stopping_phrase) <= len(value) - len(value_diff):
            return None

        if matched_phrase_index != -1:
            value = value[:matched_phrase_index]

        return postprocessed_rewrite(value), postprocessed_value(value)

class CallOp(Node):
    def __new__(cls, predecessors, lcls, glbs):
        fct, *args = predecessors
        if hasattr(fct, "__lmql_query_function__"):
            return InlineCallOp(predecessors, lcls, glbs)
        
        return super().__new__(cls)

    def __init__(self, predecessors, lcls, glbs):
        super().__init__(predecessors)
        
        self.fct, *self.args = predecessors

    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        fct, *args = args
        return fct(*args)
    
    def follow(self, *v, **kwargs):
        if any([a is None for a in v]): return None

        fct, *args = v
        return fmap(("*", fct(*args)))

@LMQLOp(["ESCAPED", "escaped"])
class EscapedOp(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def execute_predecessors(self, trace, context):
        var_op: Var = self.predecessors[0]
        assert type(var_op) is Var, "The first argument of STOPS_AT must be a direct reference to a template variable."
        return super().execute_predecessors(trace, context)
    
    def forward(self, *args, **kwargs):
        return True
    
    def follow(self, *args, **kwargs):
        return fmap(("*", True))
    
    def final(self, ops_final, operands, result, **kwargs):
        return ops_final[0]
    
    @property
    def variable(self):
        return self.predecessors[0]

    def postprocess_var(self, var_name):
        return var_name == self.predecessors[0].name

    def postprocess(self, operands, value):
        value = value.replace("\n",  "\\n")
        value = value.replace("\t",  "\\t")

        return postprocessed_rewrite(value), postprocessed_value(value)

    def postprocess_order(self, other, **kwargs):
        if isinstance(other, StopAtOp):
            return "after"
        return 0

@LMQLOp(["ERASE"])
class EraseOp(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def execute_predecessors(self, trace, context):
        var_op: Var = self.predecessors[0]
        assert type(var_op) is Var, "The first argument of STOPS_AT must be a direct reference to a template variable."
        return super().execute_predecessors(trace, context)
    
    def forward(self, *args, **kwargs):
        return True
    
    def follow(self, *args, **kwargs):
        return fmap(("*", True))
    
    def final(self, ops_final, operands, result, **kwargs):
        return ops_final[0]
    
    @property
    def variable(self):
        return self.predecessors[0]

    def postprocess_var(self, var_name):
        return var_name == self.predecessors[0].name

    def postprocess(self, operands, value):
        return postprocessed_rewrite(""), postprocessed_value(value)

    def postprocess_order(self, other, **kwargs):
        if isinstance(other, StopAtOp):
            return "after"
        return 0
class OpaqueLambdaOp(Node):
    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        fct, *args = args
        return fct(*args)
    
    def follow(self, *v, **kwargs):
        if any([a is None for a in v]): return None

        fct, *args = v
        return fmap(
            ("*", fct(*args))
        )

def execute_op_stops_at_only(variable: str, op: Node, trace, result=None, sidecondition=None):
    """
    Evaluates a Node and returns the list of defined StopAtOps for the query.
    """
    is_root_call = result is None and sidecondition is None
    
    if result is None: 
        result = []
    if sidecondition is None: 
        sidecondition = []

    if isinstance(op, StopAtOp):
        if op.predecessors[0].name == variable:
            result.append((op, sidecondition.copy()))
    elif type(op) is AndOp:
        non_stop_ops = [o for o in op.predecessors if not isinstance(o, StopAtOp)]
        for p in op.predecessors:
            execute_op_stops_at_only(variable, p, trace=trace, result=result, sidecondition=sidecondition + non_stop_ops)
    elif type(op) is OrOp:
        for p in op.predecessors:
            execute_op_stops_at_only(variable, p, trace=trace, result=result, sidecondition=sidecondition)
    elif type(op) is NotOp:
        negated_stop_ops = []
        execute_op_stops_at_only(variable, op.predecessors[0], trace=trace, result=negated_stop_ops)
        assert len(negated_stop_ops) == 0, "error: nesting stopping operators with 'not' expressions is not supported"
    else:
        # other ops are no-ops from a STOPS_AT perspective (cannot contain additional STOPS_AT ops)
        # TODO: what about not
        return []
    
    if is_root_call:
        # only return stop ops whose sidecondition are all satisfied
        result = [sp for sp, sc in result if all(trace[p][0] is None or trace[p][0] for p in sc)]
    
    return result

def execute_postprocess(op: Node, var_name: str, value: str, context=None):
    """
    Applies any postprocess() operations of the provided constraints
    to the specified variable and value.

    Returns a tuple of (postprocessed_value, rewritten_prompt)
    """
    if op is None: return value, value

    root_op = op
    nodes = [op]

    trace = {}
    expr_value = execute_op(op, trace=trace, context=context, return_final=False)
    
    postprocessors = []

    # collect and sort set of postprocessing operations
    while len(nodes) > 0:
        op = nodes.pop()
        nodes += [p for p in op.predecessors if isinstance(p, Node)]

        if op.postprocess_var(var_name):
            # compute operation inputs
            inputs = op.execute_predecessors(trace, context)
            # determine insertion index in postprocessors
            i = 0
            while i < len(postprocessors):
                current_op, current_op_inputs = postprocessors[i]
                relative_order = op.postprocess_order(current_op, operands=inputs, other_inputs=current_op_inputs)
                if relative_order == "before":
                    break
                elif relative_order == "after":
                    i += 1
                else:
                    relative_order = current_op.postprocess_order(op, operands=current_op_inputs, other_inputs=inputs)
                    if relative_order == "before":
                        i += 1
                    elif relative_order == "after":
                        break
                    else:
                        assert len(postprocessors) == 0, "The specified set of constraints contains multiple incompatible postprocessing operations for the same variable. The conflicting operations are: {} and {}. Please make sure the used constraints implement postprocess_order for each other, to use them together.".format(current_op, op)
            postprocessors.insert(i, (op, inputs))

    # filter out stopping conditions as postprocessors that were not actually triggered (due to unfulfilled sideconditions)
    stopping_conditions: List[StopAtOp] = execute_op_stops_at_only(var_name, root_op, trace)
    postprocessors = [p for p in postprocessors if not isinstance(p[0], StopAtOp) or p[0] in stopping_conditions]

    rewritten_value = None
    rewritten_prompt = value

    # apply postprocessing operations
    for pop in postprocessors:
        pop, inputs = pop # unpack to get op and inputs
        result = pop.postprocess(inputs, rewritten_prompt)

        if result is not None:
            if type(result) is tuple:
                for v in result:
                    if type(v) is postprocessed_value:
                        rewritten_value = v.value
                    elif type(v) is postprocessed_rewrite:
                        rewritten_prompt = v.rewrite
                    else:
                        assert False, "Invalid postprocess() return value: {} for {}".format(v, op)
            else:
                rewritten_value = result
    
    if rewritten_prompt is None:
        rewritten_prompt = str(value)
    if rewritten_value is None:
        rewritten_value = value
    
    return rewritten_value, rewritten_prompt