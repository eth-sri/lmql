from tokenize import Token
from typing import Iterable, Tuple, List
from itertools import product

from lmql.ops.token_set import *
from lmql.ops.follow_map import *

lmql_operation_registry = {}

# @LMQLOp('function_name') decorator
def LMQLOp(name):
    def class_transformer(cls):
        if type(name) is list:
            for n in name:
                lmql_operation_registry[n] = f"{cls.__name__}"
            return cls
        lmql_operation_registry[name] = f"{cls.__name__}"
        return cls
    return class_transformer

class Node:
    def __init__(self, predecessors):
        assert type(predecessors) is list, "Predecessors must be a list, not {}".format(type(predecessors))
        self.predecessors = predecessors
        self.depends_on_context = False
    
    def execute_predecessors(self, trace, context):
        return [execute_op(p, trace=trace, context=context) for p in self.predecessors]

    def forward(self, *args, **kwargs):
        raise NotImplementedError(type(self) + " does not implement forward()")

    def follow(self, *args, **kwargs):
        raise NotImplementedError(type(self) + " does not implement follow()")
    
    def final(self, args, **kwargs):
        if all([a == "fin" for a in args]):
            return "fin"
        return "var"

    def __nodelabel__(self):
        return str(type(self))
    
    def postprocess_var(self, var_name):
        """
        Returns true if this operations provides postprocessing semantics for complete values for the given variable name.
        """
        return False

    def postprocess(self, operands, value):
        """
        Returns the postprocessed variant of `value`. Only called if `postprocess_var` returns true for variable name of value.
        
        You can return a tuple of postprocessed_rewrite (prompt) and postprocessed_value (variable value), to additionally 
        provide different postprocessing semantics for the variable value and the rewrite of the prompt.
        """
        pass

    def postprocess_order(self, other, **kwargs):
        """
        Orders application of postprocessing operations. Returns "before", "after" or 0 if order is not defined.
        
        Only invoked for `other` operations, that return true for the same `postprocess_var`.
        """
        return 0 # by default, no order is defined (only one postprocessing operation per variable can be applied)

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
            return self.get_handler(args).forward(*args, **kwargs)
        
        def follow(self, *args, **kwargs):
            return self.get_handler(args).follow(*args, **kwargs)
        
        def final(self, *args, **kwargs):
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

NextToken = "<lmql.next>"

def is_next_token(t): 
    return t == NextToken

def strip_next_token(x):
    if type(x) is list:
        return [i for i in x if not is_next_token(i)]
    elif type(x) is tuple:
        return tuple(i for i in x if not is_next_token(i))
    if type(x) is not str:
        return x
    if x.endswith(NextToken):
        x = x[:-len(NextToken)]
    return x

class postprocessed_value:
    def __init__(self, value):
        self.value = value
class postprocessed_rewrite:
    def __init__(self, rewrite):
        self.rewrite = rewrite


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
            number_continuation_tokens = tset("0","1","2","3","4","5","6","7","8","9","00","01","10","12","50","19","11","20","30","15","14","16","13","25","18","17","24","80","40","22","60","23","29","27","26","28","99","33","70","45","35","64","75","21","38","44","36","32","39","34","05","37","48","66","55","47","08","49","09","65","07","02","04","03","68","31","67","59","06","77","58","69","88","46","57","43","42","78","79","90","95","41","56","54","98","76","52","53","51","86","74","89","72","73","96","71","63","62","85","61","97","84","87","94","92","83","93","91","82","81", exact=True, name="number_continuation_tokens")
        else:
            number_tokens = tset("[ 1-9][0-9]*$", regex=True, name="full_number_tokens")
            number_continuation_tokens = tset("[0-9]+$", regex=True, name="full_number_continuation_tokens")

        if not has_next_token:
            return fmap(
                ("eos", len(v.strip()) != 0),
                ("*", self.forward(v))
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
                    (number_continuation_tokens, True),
                    ("eos", False),
                    ("*", False)
                )

            return fmap(
                (number_continuation_tokens, True),
                ("eos", True),
                ("*", False)
            )
        
    def postprocess_var(self, var_name):
        return var_name == self.predecessors[0].name

    def postprocess(self, operands, raw):
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

class NotOp(Node):
    def forward(self, op, **kwargs):
        return not op

    def follow(self, v, **kwargs):
        return not v

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

        if type(op1) is str or type(op1) is str:
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

        if op1f == "fin" and op1 < op2 and op2f != "var":
            return "fin"
        if op2f == "fin" and op2 <= op1 and op1f != "var":
            return "fin"

        # default behavior
        if all([a == "fin" for a in operand_final]):
            return "fin"
        return "var"

EqOp = DynamicTypeDispatch("EqOp", (
    ((int, int), EqOpInt),
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

class Var(Node):
    def __init__(self, name):
        super().__init__([])
        self.name = name

        self.depends_on_context = True
        
        # indicates whether the downstream node requires text diff information
        self.diff_aware_read = False

    async def json(self):
        return self.name

    def forward(self, context, **kwargs):
        if self.diff_aware_read:
            return (context.get(self.name, None), context.get_diff(self.name, None))
        return context.get(self.name, None)
    
    def follow(self, context, **kwargs):
        value = context.get(self.name, None)
        if value is None: return None
        
        # also return the text diff if required
        if self.diff_aware_read:
            value = (value, context.get_diff(self.name, None))

        # strip_next_token but also supports tuples
        def strip_nt(v):
            if type(v) is tuple: return (strip_next_token(v[0]), v[1])
            else: return strip_next_token(v)

        return fmap(
            ("eos", PredeterminedFinal(strip_nt(value), "fin")),
            ("*", value),
        )

    def final(self, x, context, operands=None, result=None, **kwargs):
        return context.final(self.name)

    def __repr__(self) -> str:
        return f"<Var {self.name}>"

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

class OrOp(Node):
    def forward(self, *args, **kwargs):
        if any([a == True for a in args]):
            return True
        elif all([a == False for a in args]):
            return False
        else:
            return None

    def follow(self, *args, **kwargs):
        return fmap(
            ("*", self.forward(*args))
        )

    def final(self, args, operands=None, result=None, **kwargs):
        if result:
            if any(a == "fin" and v == True for a,v in zip(args, operands)):
                return "fin"
            return "var"
        else: # not result
            if any(a == "var" for a in args):
                return "var"
            return "fin"

class AndOp(Node):
    def forward(self, *args, **kwargs):
        if type(args[0]) is tuple and len(args) == 1:
            args = args[0]

        if any([a == False for a in args]):
            return False
        elif any([a is None for a in args]):
            return None
        else:
            return all([a for a in args])

    def follow(self, *v, **kwargs):
        return fmap(
            ("*", self.forward(*v))
        )

    def final(self, args, operands=None, result=None, **kwargs):
        if result:
            if all([a == "fin" for a in args]):
                return "fin"
            return "var"
        else: # not result
            if any([a == "fin" and v == False for a,v in zip(args, operands)]):
                return "fin"
            return "var"

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

@LMQLOp("STARTS_WITH")
class StartsWithOp(Node):
    def forward(self, *args, **kwargs):
        if any([a is None for a in args]): return None
        
        x = args[0]
        allowed_phrases = args[1]

        for phrase in allowed_phrases:
            if x.startswith(phrase):
                return True

        return False

    def follow(self, *args, **kwargs):
        if any([a is None for a in args]): return None

        x = args[0]
        allowed_phrases = args[1]

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
        self._tokenized_stopping_phrase_cache = {}

    def execute_predecessors(self, trace, context):
        var_op: Var = self.predecessors[0]
        assert type(var_op) is Var, "The first argument of STOPS_AT must be a direct reference to a template variable."
        assert type(self.predecessors[1]) is str, "The second argument of STOPS_AT must be a string literal."
        var_op.diff_aware_read = True
        return super().execute_predecessors(trace, context)
    
    @property
    def variable(self):
        return self.predecessors[0]

    async def stopping_phrase_tokenized(self, tokenizer):
        if tokenizer in self._tokenized_stopping_phrase_cache:
            return self._tokenized_stopping_phrase_cache[tokenizer]
        else:
            result = (await tokenizer(self.stopping_phrase))
            self._tokenized_stopping_phrase_cache[tokenizer] = result
            return result

    def forward(self, *args, final, **kwargs):
        if any([a is None for a in args]): return None

        if all([a == "fin" for a in final]):
            return True

        op1, op1_diff = args[0]
        op2 = args[1]

        if op1 is None: return
        if op1_diff is None: op1_diff = ""

        matched_phrase_index = op1.rfind(op2)
        op2_in_op1 = matched_phrase_index != -1 and matched_phrase_index + len(op2) > len(op1) - len(op1_diff)

        return not op2_in_op1 or op1.endswith(op2)

    def follow(self, *args, previous_result=None, **kwargs):
        if any([a is None for a in args]): 
            return None

        op1, op1_diff = args[0]
        if op1 is None: return None
        if op1_diff is None: op1_diff = ""

        op1 = strip_next_token(op1)
        op2 = args[1]

        matched_phrase_index = op1.rfind(op2)
        op2_in_op1 = matched_phrase_index != -1 and matched_phrase_index + len(op2) > len(op1) - len(op1_diff)

        if not op2_in_op1: return fmap(("*", True))

        ends_with_stopping_phrase = op1.endswith(op2)

        if op1 != args[0][0] and ends_with_stopping_phrase:
            # print("StopAtOp.follow()", [op1], [op2], valid)
            ends_with_stopping_phrase = False
        if len(op1) == 0:
            ends_with_stopping_phrase = True
        
        return fmap(("*", ends_with_stopping_phrase))

    def final(self, ops_final, operands, result, **kwargs):
        if result: 
            if ops_final[0] == "var":
                return "var"
            return "fin"
        else: # not result
            if ops_final[0] == "var": 
                r = "var"
            elif ops_final[0] == "dec": 
                r = "var"
            else: 
                r = "fin"
            return r

    def postprocess_var(self, var_name):
        return var_name == self.predecessors[0].name

    def postprocess(self, operands, value):
        op2 = operands[1]
        matched_phrase_index = value.rfind(op2)
        if matched_phrase_index != -1:
            value = value[:matched_phrase_index + len(op2)]

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
        op2 = operands[1]
        matched_phrase_index = value.find(op2)
        if matched_phrase_index != -1:
            value = value[:matched_phrase_index]

        return postprocessed_rewrite(value), postprocessed_value(value)
    
    @property
    def stopping_phrase(self):
        return self.predecessors[1]

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

def create_mask(follow_map, valid, final):
    if follow_map is None:
        return "*"
    
    allowed_tokens = tset()
    otherwise_result = None

    for pattern, result in follow_map:
        if pattern == "*":
            otherwise_result = result

        if result is not None:
            value, final = result
        else:
            value = None
            final = "var"

        if value == True or value is None:
            allowed_tokens = union(allowed_tokens,pattern)
        elif value == False and final == ("var",):
            allowed_tokens = union(allowed_tokens, pattern)
        elif value is None and len(follow_map.components) == 1:
            allowed_tokens = "*"
        elif result == (False, ('fin',)):
            if pattern != "*":
                allowed_tokens = setminus(allowed_tokens, pattern)

    if allowed_tokens == "∅":
        return tset("eos")

    if len(allowed_tokens) == 0:
        if otherwise_result is not None:
            othw_value, othw_final = otherwise_result
        else:
            othw_value, othw_final = None, "var"
        if not othw_value and othw_final == ("fin",):
            return tset("eos")
        else:
            return "*"

    return allowed_tokens

def is_node(op):
    return issubclass(type(op), Node)

def derive_predecessor_final(op, trace):
    def get_final(v):
        # for nodes, get final value from trace
        if is_node(v): return trace[v][1]
        # for constants, final value is always "fin"
        return "fin"
    return [get_final(p) for p in op.predecessors]

def derive_final(op, trace, context, result):
    predecessor_final = derive_predecessor_final(op, trace)

    def get_predecessor_result(v):
        if is_node(v): return trace[v][0]
        return v
    
    predecessor_values = [get_predecessor_result(p) for p in op.predecessors]

    context_arg = ()
    if op.depends_on_context: 
        context_arg += (context,)
    
    return op.final(predecessor_final, *context_arg, operands=predecessor_values, result=result)

def execute_op_stops_at_only(op: Node, result=None):
    """
    Evaluates a Node and returns the list of defined StopAtOps for the query.
    """
    if result is None: result = []

    if type(op) is StopBeforeOp:
        result.append(op)
    elif type(op) is AndOp:
        for p in op.predecessors:
            execute_op_stops_at_only(p, result=result)
    elif type(op) is OrOp:
        subresults = []
        for p in op.predecessors:
            subresult = []
            execute_op_stops_at_only(p, result=subresult)
            subresults.append(subresult)
        # intersect subresults
        result += list(set.intersection(*[set(r) for r in subresults]))

    else:
        # other ops are no-ops from a STOPS_AT perspective (cannot contain additional STOPS_AT ops)
        # TODO: what about not
        return []
    return result

def execute_postprocess(op: Node, var_name: str, value: str, trace=None, context=None):
    """
    Applies any postprocess() operations of the provided constraints
    to the specified variable and value.

    Returns a tuple of (postprocessed_value, rewritten_prompt)
    """
    if op is None: return value, value

    nodes = [op]

    trace = {}
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
                    assert len(postprocessors) == 0, "The specified set of constraints contains multiple incompatible postprocessing operations for the same variable. The conflicting operations are: {} and {}. Please make sure the used constraints implement postprocess_order for each other, to use them together.".format(current_op, op)
            postprocessors.insert(i, (op, inputs))
    
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

def execute_op(op: Node, trace=None, context=None, return_final=False):
    # for constant dependencies, just return their value
    if not is_node(op): 
        return op
    
    # only evaluate each operation once
    if op in trace.keys(): 
        return trace[op][0]
    
    # compute predecessor values
    inputs = op.execute_predecessors(trace, context)
    
    if op.depends_on_context: 
        inputs += (context,)

    inputs_final = derive_predecessor_final(op, trace)
    result = op.forward(*inputs, final=inputs_final)
    is_final = derive_final(op, trace, context, result)
    
    if trace is not None: 
        trace[op] = (result, is_final)

    if return_final:
        return result, is_final

    return result

def digest(expr, context, follow_context, no_follow=False):
    if expr is None: return True, "fin", {}, {}

    trace = {}
    follow_trace = {}
    expr_value, is_final = execute_op(expr, trace=trace, context=context, return_final=True)

    if no_follow:
        return expr_value, is_final, trace, follow_trace

    for op, value in trace.items():
        # determine follow map of predecessors
        if len(op.predecessors) == 0: 
            # empty argtuple translates to no follow input
            intm = all_fmap((ArgTuple(), ["fin"])) 
        else:
            # use * -> value, for constant value predecessor nodes
            def follow_map(p):
                if is_node(p): return follow_trace[p]
                else: return fmap(("*", (p, ("fin",))))
            intm = fmap_product(*[follow_map(p) for p in op.predecessors])
        
        # apply follow map
        op_follow_map = follow_apply(intm, op, value, context=follow_context)

        # name = op.__class__.__name__
        # print(name, value)
        # print("follow({}) = {}".format(name, op_follow_map))

        follow_trace[op] = op_follow_map
    
    return expr_value, is_final, trace, follow_trace
