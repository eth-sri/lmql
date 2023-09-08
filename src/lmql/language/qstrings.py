from typing import List, Optional, Dict
from dataclasses import dataclass

import tokenize
import io

@dataclass
class TemplateVariable:
    name: str    
    type_expr: str = None
    decoder_expr: str = None
    decorator_exprs: Optional[List[str]] = None
    function_call: str = None

    # populated after first parse
    index: int = None

    def __post_init__(self):
        if "(" in self.name:
            import ast
            call = ast.parse(self.name).body[0].value
            assert type(call) is ast.Call, "Failed to parse template variable name as function call: {}".format(self.name)
            assert len(call.args) >= 1, "A function call has to have at least the template variable name as argument: {}".format(self.name)
            self.name = ast.unparse(call.args[0]).strip()
            self.function_call = ast.unparse(call).strip()

    def __str__(self):
        r = " ".join([f"@{d}" for d in self.decorator_exprs or []] + \
                    ([self.decoder_expr] if self.decoder_expr is not None else []) + \
                     [self.function_call or self.name] + \
                    ([f": {self.type_expr}"] if self.type_expr is not None else []))
        return f"[{r}]"

    def variable_args(self, query_args: Dict):
        # given a list of qstring args (e.g. list of decoders, types, etc.), selects
        # the ones that apply to this variable
        args = {k: v[self.index] if type(v) is list else v for k, v in query_args.items()}
        
        # remove None decorators
        if args.get("decorators") is None:
            args.pop("decorators", None)
        
        return args

@dataclass
class FExpression:
    expr: str

    def __str__(self):
        return f"{{{self.expr}}}"

@dataclass
class DistributionVariable:
    name: str

    def __str__(self):
        return f"[@distribution {self.name}]"

@dataclass
class TagExpression:
    tag: str

    def __str__(self):
        return f"{{{self.tag}}}"

def qstring_to_stmts(qstring, mode="square-only"):
    return QstringParser(mode=mode).parse(qstring)

def unescape_qstring(qstring):
    return qstring.replace("[[", "[").replace("]]", "]")

def stmts_to_qstring(stmts):
    return "".join(str(s) for s in stmts)

class TokenCursor:
    def __init__(self, s):
        self.tokens = tokenize.generate_tokens(io.StringIO(s).readline)
        self.token = next(self.tokens)
        self.s = s

    def n_to_skip(self):
        end_line = self.token.end[0] - 1
        lines = self.s.split("\n")
        n = 0
        for i, line in enumerate(lines):
            if i >= end_line:
                break
            n += len(line) + 1
        return n + self.token.end[1]

    def next(self):
        self.token = next(self.tokens)

class QstringParser:
    def __init__(self, mode="all"):
        self.mode = mode
        self.s = None

    def lookahead(self, n=1):
        return "".join(self.s[1:1+n])

    def skip(self, n, swallow=False):
        if not swallow:
            if self.state == "string":
                self.stmts[-1] += self.s[:n]
            elif self.state == "template variable":
                self.stmts[-1].name += self.s[:n]
            elif self.state == "f-expr":
                self.stmts[-1].expr += self.s[:n]
            else:
                assert False, "Invalid qstring parser state: {}".format(self.state)
        self.s = self.s[n:]

    def parse(self, s: str):
        self.state = "string" # | "template variable" | "f-expr"
        self.s = s
        
        self.stmts = [""]

        while len(self.s) > 0:
            c = self.s[0]

            if self.state == "string":
                if c == "[":
                    if self.lookahead() == "[":
                        self.skip(2)
                        continue
                    else:
                        self.state = "template variable"
                        if len(self.stmts[-1]) == 0:
                            self.stmts = self.stmts[:-1]
                        self.stmts.append(TemplateVariable(""))
                        self.skip(1, swallow=True)
                        continue
                elif c == "{" and self.mode == "all":
                    if self.lookahead() == "{":
                        self.skip(2)
                        continue
                    else:
                        self.state = "f-expr"
                        if len(self.stmts[-1]) == 0:
                            self.stmts = self.stmts[:-1]
                        self.stmts.append(FExpression(""))
                        self.skip(1, swallow=True)
                        continue
                else:
                    self.skip(1)
                    continue
            elif self.state == "template variable":
                self.parse_template_var()
                self.state = "string"
                self.stmts.append("")
                continue
            elif self.state == "f-expr":
                if c == "}":
                    self.state = "string"
                    self.stmts.append("")
                    self.skip(1, swallow=True)
                    continue
                else:
                    self.skip(1)
                    continue
        if type(self.stmts[-1]) is str and len(self.stmts[-1]) == 0:
            self.stmts = self.stmts[:-1]
        
        # assign indices to template variables
        variable_counter = 0

        for i, s in enumerate(self.stmts):
            if type(s) is TemplateVariable:
                s.index = variable_counter
                variable_counter += 1
            
                if "distribution" in (s.decorator_exprs or []):
                    self.stmts[i] = DistributionVariable(s.name)
                    continue

            if type(s) is FExpression and s.expr.startswith(":"):
                self.stmts[i] = TagExpression(s.expr)

        # filter out empty name template variables
        self.stmts = [s for s in self.stmts if not (type(s) is TemplateVariable and len(s.name) == 0)]

        return self.stmts
    
    def parse_identifier_or_function_call(self, cursor):
        assert cursor.token.type == tokenize.NAME, "Expected identifier, got {}".format(cursor.token)
        name = cursor.token.string

        # check for field access
        cursor.next()
        while cursor.token.type == tokenize.OP and cursor.token.string == ".":
            cursor.next()
            assert cursor.token.type == tokenize.NAME, "Expected identifier, got {}".format(cursor.token)
            name += "." + cursor.token.string
            cursor.next()


        # check for function call
        if not (cursor.token.type == tokenize.OP and cursor.token.string == "("):
            return name
        
        # parse function call
        assert cursor.token.type == tokenize.OP and cursor.token.string == "(", "Expected '(', got {}".format(cursor.token)
        num_parens_to_close = 1

        arg_tokens = [cursor.token]
        while True:
            cursor.next()
            if cursor.token.type == tokenize.OP and cursor.token.string == "(":
                num_parens_to_close += 1
                arg_tokens.append(cursor.token)
            elif cursor.token.type == tokenize.OP and cursor.token.string == ")":
                num_parens_to_close -= 1
                if num_parens_to_close == 0:
                    arg_tokens.append(cursor.token)
                    cursor.next()
                    break
                else:
                    arg_tokens.append(cursor.token)
            else:
                arg_tokens.append(cursor.token)
        
        return name + tokenize.untokenize(arg_tokens).strip()

    def parse_decorators(self, cursor):
        assert cursor.token.type == tokenize.OP and cursor.token.string == "@", "Expected '@', got {}".format(cursor.token)
        cursor.next()

        decorators = [self.parse_identifier_or_function_call(cursor)]

        if cursor.token.type == tokenize.OP and cursor.token.string == "@":
            return decorators + self.parse_decorators(cursor)
        else:
            return decorators

    def parse_template_var(self):
        name = None
        decoder = None
        decorators = None
        
        cursor = TokenCursor(self.s)

        # check for decorator
        if cursor.token.type == tokenize.OP and cursor.token.string == "@":
            decorators = self.parse_decorators(cursor)

        # parse variable name
        name = self.parse_identifier_or_function_call(cursor)
        
        # check for end of variable
        if cursor.token.type == tokenize.OP and cursor.token.string == "]":
            self.state = "string"
            self.stmts[-1] = TemplateVariable(name, decorator_exprs=decorators)
            self.skip(cursor.n_to_skip(), swallow=True)
            self.state = "string"
            return
            
        # check for another identifier (e.g. name is actually decoder or decorator)
        elif cursor.token.type == tokenize.NAME:
            decoder = name
            name = self.parse_identifier_or_function_call(cursor)

        # check for end 
        if cursor.token.type == tokenize.OP and cursor.token.string == "]":
            self.state = "string"
            self.stmts[-1] = TemplateVariable(name, decoder_expr=decoder, decorator_exprs=decorators)
            self.skip(cursor.n_to_skip(), swallow=True)
            self.state = "string"
            return

        # otherwise, expect type annotation
        assert cursor.token.type == tokenize.OP and cursor.token.string == ":", "Unexpected token in template variable: {}".format(cursor.token)

        # allow anything until we hit the final closing bracket
        squared_brackets_to_close = 0

        type_tokens = []
        while True:
            cursor.next()

            if cursor.token.type == tokenize.OP and cursor.token.string == "[":
                squared_brackets_to_close += 1
                type_tokens.append(cursor.token)
            elif cursor.token.type == tokenize.OP and cursor.token.string == "]":
                if squared_brackets_to_close == 0:
                    break
                else:
                    squared_brackets_to_close -= 1
                    type_tokens.append(cursor.token)
            else:
                type_tokens.append(cursor.token)
        
        self.state = "string"
        self.stmts[-1] = TemplateVariable(name, tokenize.untokenize(type_tokens).strip(), decoder_expr=decoder, decorator_exprs=decorators)
        self.skip(cursor.n_to_skip(), swallow=True)
        self.state = "string"