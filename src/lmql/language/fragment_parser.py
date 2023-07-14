from dataclasses import dataclass, field
import tokenize
from io import StringIO
from typing import Any, List
import astunparse
import ast
import sys
import termcolor

import lmql.runtime.dclib.decoders
from lmql.runtime.dclib import get_all_decoders

class FragmentParserError(Exception): pass

@dataclass
class LMQLDecoderConfiguration:
    method: ast.AST
    decoding_args: List[ast.keyword]

    @property
    def has_dump_compiled_code_flag(self):
        for kwa in self.decoding_args:
            if kwa.arg == "dump_compiled_code":
                if type(kwa.value) is ast.Constant and kwa.value.value == True:
                    return True
        return False

@dataclass
class LMQLDistributionClause:
    variable_name: str
    values: List[str]

@dataclass
class LMQLQuery:
    # all code that comes before the first decode keyword
    prologue: list = field(default_factory=list)

    decode_str: list = field(default_factory=list)
    decode = None
    
    prompt_str: list = field(default_factory=list)
    prompt = None

    from_str: list = field(default_factory=list)
    from_ast = None

    where_str: list = field(default_factory=list)
    where = None
    where_expr = None

    distribution_str: list = field(default_factory=list)
    distribution = None
    distribution_expr = None

    scoring_str: list = field(default_factory=list)
    scoring = None

    scope = None

def is_keyword(tok, kw):
    return tok.type == tokenize.NAME and tok.string.lower() == kw.lower()

def remove_indentation(s, oneline=False):
    # print([s])
    lines = []

    min_indent = " " * len(s)

    for line in s.split("\n"):
        if line.strip() == "" or line == "\\": continue
        unindented_line = line.lstrip()
        line_indent = len(line) - len(unindented_line)
        min_indent = min_indent if len(min_indent) < line_indent else line[:line_indent]
        # print(unindented_line, [line[:line_indent], line], line_indent)
        
        # buf = StringIO(line)
        # toks = [t for t in tokenize.generate_tokens(buf.readline)]
        # print(tokenize.tok_name[toks[-4].type])
        
        # lines.append(line.lstrip())

    # print("min_indent is", len(min_indent), [min_indent])

    for line in s.split("\n"):
        if line.strip() == "" or line == "\\": continue
        assert line.startswith(min_indent)

        lines.append(line[len(min_indent):])

    if oneline:
        return " \\\n".join(lines)
    else:
        return "\n".join(lines)

def remove_comments(s):
    if type(s) is str: return s
    assert type(s) is list
    return tokenize.untokenize([transform_token(t) for t in s if t.type != tokenize.COMMENT])

def transform_token(t):
    return t

def ast_parse(s, unindent=False, oneline=False, loc=None):
    # for special symbols
    if len(s) > 0 and all(type(e) is str for e in s): return ast.parse('"' + " ".join(s) + '"')
    try:
        s = remove_comments(s)
        if unindent: s = remove_indentation(s, oneline=oneline)
        return ast.parse(s)
    except SyntaxError as e:
        msg = ""
        
        msg += "Failed to parse {} clause of the query ({}):\n\n".format(loc, e.msg)
        
        for lineno, line in enumerate(s.split("\n")):
            if lineno + 1 == e.lineno:
                msg += "\t" + line[:e.offset - 1]
                msg += termcolor.colored(line[e.offset - 1:], "red") + "\n"
                msg += "\t" + ((e.offset - 1) * " ") + "^\n"
                break
            elif abs(lineno + 1 - e.lineno) < 2:
                msg += "\t" + line + "\n"
        
        raise FragmentParserError(msg)

def tok_str(tok):
    if tok.type == tokenize.NAME and tok.string == "AND":
        return "and"
    if tok.type == tokenize.NAME and tok.string == "OR":
        return "and"
    if tok.type == tokenize.NAME and tok.string == "IN":
        return "in"
    if tok.type == tokenize.NAME and tok.string == "NOT":
        return "not"
    if tok.type == tokenize.NAME and tok.string == "AS":
        return "as"
    return tok.string

class LanguageFragmentParser:
    def __init__(self):
        self.state = "start" # "decode" | "prompt" | "where" | "scoring" | "import"
        self.query = LMQLQuery()
        self.paren_count = 0

    def parse(self, readline):
        for i, tok in enumerate(tokenize.generate_tokens(readline)):
            self.digest(tok)
        
        if self.state == "start":
            self.query.prompt_str = self.query.prologue
            self.query.prologue = []
            self.state = "prompt"

        # print("decode_str", remove_comments(self.query.decode_str))
        # print("prompt_str", remove_comments(self.query.prompt_str))
        # print("from_str", remove_comments(self.query.from_str))

        self.prologue_transform()
        self.inline_where_transform()
        self.ast_parse()
        self.syntax_validation()
        self.ast_transform()

        return self.query

    def inline_where_transform(self):
        prompt_tokens = self.query.prompt_str
        for i in range(len(prompt_tokens) - 1):
            tok = prompt_tokens[i]
            lookahead = prompt_tokens[i+1]
            if tok.type == tokenize.STRING and lookahead.type == tokenize.NAME and lookahead.string == "where":
                # print(prompt_tokens[i+1])
                prompt_tokens[i+1] = tokenize.TokenInfo(type=tokenize.OP, string="and", start=lookahead.start, end=lookahead.end, line=lookahead.line)
        

    def prologue_transform(self):
        # translate prologue tokens into str
        self.query.prologue = tokenize.untokenize(self.query.prologue)

    def ast_transform(self):
        if self.query.distribution is not None:
            # this structure is already validated (see self.syntax_validation)
            variable_name = self.query.distribution.left.id
            self.query.distribution = LMQLDistributionClause(variable_name, self.query.distribution.comparators[0])

    def syntax_validation(self):
        # validation distribution clause
        if self.query.distribution is not None:
            error_msg = "The distribution clause must be formed like 'VAR in [list of values]'."
            if type(self.query.distribution) is not ast.Compare:
                raise FragmentParserError(error_msg)
            if type(self.query.distribution.ops[0]) is not ast.In:
                raise FragmentParserError(error_msg)
            variable_node = self.query.distribution.left
            if type(variable_node) is not ast.Name:
                raise FragmentParserError(error_msg)
            values_list = self.query.distribution.comparators[0]

    def ast_parse(self):
        # parse decode, prompt and from
        decode_body = ast_parse(self.query.decode_str, loc="decode").body
        if len(decode_body) > 0:
            self.query.decode = decode_body[0].value
        else:
            # default decoder
            self.query.decode = ast.parse("__dynamic__").body[0].value
        
        self.query.prompt = ast_parse(self.query.prompt_str, unindent=True, loc="prompt").body
        
        from_body = ast_parse(self.query.from_str, unindent=True, loc="from").body
        if len(from_body) > 0:
            self.query.from_ast = from_body[0]
        else:
            self.query.from_ast = ast.Str(s="<dynamic>")

        where_body = ast_parse(self.query.where_str, unindent=True, oneline=True, loc="where").body
        if len(where_body) > 0:
            self.query.where = where_body[0]
        else:
            self.query.where = None
        
        # parse distribution clause if present
        self.query.distribution = ast_parse(self.query.distribution_str, unindent=True, loc="distribution").body
        if len(self.query.distribution) > 0: 
            self.query.distribution = self.query.distribution[0].value
        else:
            self.query.distribution = None

        scoring_body = ast_parse(self.query.scoring_str, unindent=True, loc="scoring").body
        if len(scoring_body) > 0:
            self.query.scoring = scoring_body[0]
        else:
            self.query.scoring = None

    def digest(self, tok):
        if self.state == "start":
            if tok.type == tokenize.NAME:
                # when we encounter the first decoder keyword, we switch to the query parsing state
                if tok.string.lower() in get_all_decoders():
                    self.query.decode_str += [tok]
                    self.state = "decode"
                    return
            
            if is_keyword(tok, "where"):
                self.query.prompt_str = self.query.prologue + [tok]
                self.query.prologue = []
                self.state = "prompt"
                return

            # otherwise add token to prologue tokens (e.g. imports, comments, function definitions)
            self.query.prologue.append(tok)
            return
        elif self.state == "decode":
            if tok.type == tokenize.STRING and self.paren_count == 0:
                self.state = "prompt"
                self.query.prompt_str += [tok]
                return
            
            self.query.decode_str += [tok]

            if tok.type == tokenize.OP and tok_str(tok) == "(":
                self.paren_count += 1
            elif tok.type == tokenize.OP and tok_str(tok) == ")":
                self.paren_count -= 1
            if self.paren_count == 0:
                self.state = "prompt"
        elif self.state == "prompt":
            if is_keyword(tok, "where"):
                if self.query.prompt_str[-1].type != tokenize.STRING:
                    self.state = "where"
                    return
            
            if is_keyword(tok, "FROM"):
                self.state = "from"
                return
            if is_keyword(tok, "SCORING"):
                self.state = "scoring"
                return
            if is_keyword(tok, "DISTRIBUTION"):
                self.state = "distribution"
                return
            
            # if last token is NAME and current is str
            if len(self.query.prompt_str) > 0 and self.query.prompt_str[-1].type == tokenize.NAME and \
                tok.type == tokenize.STRING:
                last_tok = self.query.prompt_str[-1]
                try:
                    untokenized = tokenize.untokenize([last_tok, tok]).split(last_tok.string)[1]
                    if not untokenized.startswith(" "):
                        # print("merge name and tok", last_tok, tok)
                        self.query.prompt_str.pop(-1)
                except:
                    pass
            self.query.prompt_str += [tok]
        elif self.state == "from":
            if is_keyword(tok, "WHERE"):
                self.state = "where"
                return
            if is_keyword(tok, "SCORING"):
                self.state = "scoring"
                return
            if is_keyword(tok, "DISTRIBUTION"):
                self.state = "distribution"
                return

            self.query.from_str += [tok]
        elif self.state == "where":
            if is_keyword(tok, "SCORING"):
                self.state = "scoring"
                return
            if is_keyword(tok, "DISTRIBUTION"):
                self.state = "distribution"
                return

            self.query.where_str += [tok]
        elif self.state == "distribution":
            self.query.distribution_str += [tok]
