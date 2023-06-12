import re
from dataclasses import dataclass

@dataclass
class TemplateVariable:
    name: str

    def __str__(self):
        return f"[{self.name}]"

@dataclass
class FExpression:
    expr: str

    def __str__(self):
        return f"{{{self.expr}}}"

@dataclass
class DistributionVariable:
    name: str

    def __str__(self):
        return f"[distribution:{self.name}]"

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

class QstringParser:
    def __init__(self, mode="all"):
        self.mode = mode
        self.s = None

    def lookahead(self, n=1):
        return "".join(self.s[1:1+n])

    def parse(self, s: str):
        self.state = "string" # | "template variable" | "f-expr"
        self.s = s
        
        self.stmts = [""]

        def skip(n, swallow=False):
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

        while len(self.s) > 0:
            c = self.s[0]

            if self.state == "string":
                if c == "[":
                    if self.lookahead() == "[":
                        skip(2)
                        continue
                    else:
                        self.state = "template variable"
                        self.stmts.append(TemplateVariable(""))
                        skip(1, swallow=True)
                        continue
                elif c == "{" and self.mode == "all":
                    if self.lookahead() == "{":
                        skip(2)
                        continue
                    else:
                        self.state = "f-expr"
                        self.stmts.append(FExpression(""))
                        skip(1, swallow=True)
                        continue
                else:
                    skip(1)
                    continue
            elif self.state == "template variable":
                if c == "]":
                    self.state = "string"
                    self.stmts.append("")
                    skip(1, swallow=True)
                    continue
                # if c is not in [A-Za-z0-9:_], then it's not a valid template variable name
                elif not re.match("[A-Za-z0-9:_]", c):
                    self.state = "string"

                    self.stmts[-1] = "[" + self.stmts[-1].name
                    # merge if previous stmt is also a string
                    if type(self.stmts[-2]) is str:
                        self.stmts[-2] += self.stmts[-1]
                        self.stmts = self.stmts[:-1]

                    # check if we can directly transition into a f-expr
                    if self.mode == "all" and c == "{":
                        self.state = "f-expr"
                        self.stmts.append(FExpression(""))
                        skip(1, swallow=True)
                        continue
                    else:
                        self.stmts[-1] += c
                    
                    skip(1, swallow=True)
                    continue
                else:
                    skip(1)
                    continue
            elif self.state == "f-expr":
                if c == "}":
                    self.state = "string"
                    self.stmts.append("")
                    skip(1, swallow=True)
                    continue
                else:
                    skip(1)
                    continue
        if type(self.stmts[-1]) is str and len(self.stmts[-1]) == 0:
            self.stmts = self.stmts[:-1]
        
        for i, s in enumerate(self.stmts):
            if type(s) is TemplateVariable and s.name.startswith("distribution:"):
                self.stmts[i] = DistributionVariable(s.name[len("distribution:"):])
            elif type(s) is FExpression and s.expr.startswith(":"):
                self.stmts[i] = TagExpression(s.expr)

        # filter out empty name template variables
        self.stmts = [s for s in self.stmts if not (type(s) is TemplateVariable and len(s.name) == 0)]

        return self.stmts