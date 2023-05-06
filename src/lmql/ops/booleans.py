from .node import *
from .booleans import *

class NotOp(Node):
    def forward(self, op, **kwargs):
        return not op

    def follow(self, v, **kwargs):
        return not v

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
