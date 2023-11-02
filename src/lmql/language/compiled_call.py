"""
AST recast of a call to lmql.runtime_support.interrupt_call('call', target, args)
"""
import ast
from typing import List
from dataclasses import dataclass

@dataclass
class CompiledCall:
    func: ast.Expr
    args: list[ast.Expr]
    keywords: List[ast.keyword]
    
    @classmethod
    def view(cls, node: ast.Call):
        func = node.func
        compiled_args = node.args

        # check for interrupt_call s of type 'call'
        if ast.unparse(func) != "lmql.runtime_support.interrupt_call":
            return node
        call_type = compiled_args[0]
        if type(call_type) is not ast.Constant or call_type.value != "call":
            return node
        
        target = compiled_args[1]
        args_dict = compiled_args[2]

        if type(args_dict) is not ast.Dict:
            return node
        
        args_dict_keys = [ast.unparse(k) for k in args_dict.keys]
        items = dict(zip(args_dict_keys, args_dict.values))
        
        args = items.get("'args'", ast.Constant(value=[], kind=None)) # default to empty list
        if type(args) is ast.Call and ast.unparse(args.func) == "tuple":
            if len(args.args) > 0 and type(args.args[0]) is ast.List:
                args = args.args[0].elts

        keywords = items.get("'kwargs'", [])
        if type(keywords) is ast.Dict:
            def key_to_identifier(key):
                if type(key) is ast.Constant:
                    return key.value
                return key
            keywords = [
                ast.keyword(key_to_identifier(key),value) for key,value in zip(keywords.keys, keywords.values)
            ]

        return cls(func=target, args=args, keywords=keywords)
    
    def __repr__(self):
        args_repr = ", ".join([ast.unparse(a) for a in self.args])
        return f"CompiledCall(func={ast.unparse(self.func)}, args=({args_repr}), keywords={ast.unparse(self.keywords) if self.keywords else None})"