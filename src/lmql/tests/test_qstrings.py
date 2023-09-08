from lmql.language.qstrings import QstringParser, TemplateVariable, FExpression, DistributionVariable, TagExpression
from lmql.tests.expr_test_utils import run_all_tests

def assert_parse(qstring, expected, mode="all"):
    r = QstringParser(mode=mode).parse(qstring)
    
    assert r == expected, f"Expected {expected}, got {r}"

def test_qstrings():
    assert_parse("hello [world]", ["hello ", TemplateVariable("world", index=0)])
    assert_parse("hello [[world]]", ["hello [[world]]"])
    assert_parse("hello [[[world]]]", ["hello [[", TemplateVariable("world", index=0), "]]"])
    assert_parse("hello [[[[world]]]]", ["hello [[[[world]]]]"])

    # with curly
    assert_parse("hello {{world}}", ["hello {{world}}"])
    assert_parse("hello {{{world}}}", ["hello {{", FExpression("world"), "}}"])
    assert_parse("hello {{{{world}}}}", ["hello {{{{world}}}}"])

    # both
    assert_parse("hello [[world]] {{world}}", ["hello [[world]] {{world}}"])
    assert_parse("hello [[world]] {{{world}}}", ["hello [[world]] {{", FExpression("world"), "}}"])
    assert_parse("hello [[world]] {{{{world}}}}", ["hello [[world]] {{{{world}}}}"])
    assert_parse("hello [world] {world} ", ["hello ", TemplateVariable("world", index=0), " ", FExpression("world"), " "])

    # nested (not allowed with new parser)
    # assert_parse("hello [world [[nested]]]", ["hello [world [[nested]]]"])
    # assert_parse("hello [world [nested]]", ["hello [world ", TemplateVariable("nested", index=0), "]"])
    
    # trailing/leading/dangling
    assert_parse("hello [world]]", ["hello ", TemplateVariable("world", index=0), "]"])
    assert_parse("[[hello world]", ["[[hello world]"])
    
    # also not allowed with new parser
    # assert_parse("[ [hello]", ["[ ", TemplateVariable("hello", index=0)])

    # square in curly
    assert_parse("hello {world [nested]}", ["hello ", FExpression("world [nested]")])
    
    # curly in square (not allowed with new parser)
    # assert_parse("hello [world{nested}]", ["hello [world", FExpression("nested"), "]"])
    # assert_parse("hello [world {nested}]", ["hello [world ", FExpression("nested"), "]"])

    # mode square-only
    assert_parse("hello [world]", ["hello ", TemplateVariable("world", index=0)], mode="square-only")
    assert_parse("hello {hi} [world]", ["hello {hi} ", TemplateVariable("world", index=0)], mode="square-only")

    assert_parse("hello {{world}}", ["hello {{world}}"], mode="square-only")
    assert_parse("hello {{{world}}}", ["hello {{{world}}}"], mode="square-only")
    assert_parse("hello {{{{world}}}}", ["hello {{{{world}}}}"], mode="square-only")
    assert_parse("hello [world] {world} ", ["hello ", TemplateVariable("world", index=0), " {world} "], mode="square-only")
    assert_parse("hello {world} [world]", ["hello {world} ", TemplateVariable("world", index=0)], mode="square-only")


def test_with_types_and_decorators():
    assert_parse("[[a]] [[b]] [[c]]", ["[[a]] [[b]] [[c]]"])
    assert_parse("[[a]] {{b}} [[c]]", ["[[a]] {{b}} [[c]]"])

    # simple qstring
    assert_parse("Hello[WHO]", ["Hello", TemplateVariable("WHO", index=0)])
    assert_parse("[WHO]", [TemplateVariable("WHO", index=0)])
    assert_parse("Hello[WHO]{abc}", ["Hello", TemplateVariable("WHO", index=0), FExpression("abc")])
    assert_parse("Hello[WHO]!", ["Hello", TemplateVariable("WHO", index=0), "!"])

    # with f-exprs
    assert_parse("Hello[WHO]! {a}", ["Hello", TemplateVariable("WHO", index=0), "! ", FExpression("a")])

    # multiple place holders
    assert_parse("Hello[WHO][WHAT]!", ["Hello", TemplateVariable("WHO", index=0), TemplateVariable("WHAT", index=1), "!"])

    # tag expr
    assert_parse("Hello[WHO]! {:b}", ["Hello", TemplateVariable("WHO", index=0), "! ", TagExpression(":b")])

    # type variable
    assert_parse("Hello[WHO:int]!", ["Hello", TemplateVariable("WHO", type_expr="int", index=0), "!"])
    assert_parse("Hello[WHO: int]!", ["Hello", TemplateVariable("WHO", type_expr="int", index=0), "!"])
    assert_parse("Hello[WHO:List[int]]!", ["Hello", TemplateVariable("WHO", type_expr="List[int]", index=0), "!"])
    assert_parse("Hello[WHO: List[int]]!", ["Hello", TemplateVariable("WHO", type_expr="List[int]", index=0), "!"])
    assert_parse("Hello[WHO:Person]!", ["Hello", TemplateVariable("WHO", type_expr="Person", index=0), "!"])
    assert_parse("Hello[WHO:f(1,2,{'a':3}]!", ["Hello", TemplateVariable("WHO", type_expr="f(1,2,{'a':3}", index=0), "!"])
    
    # with variable decoder
    assert_parse("Hello[argmax WHO]!", ["Hello", TemplateVariable("WHO", decoder_expr="argmax", index=0), "!"])
    assert_parse("Hello[sample(n=2) WHO]!", ["Hello", TemplateVariable("WHO", decoder_expr="sample(n=2)", index=0), "!"])
    assert_parse("Hello[argmax WHO:f(1,2,{'a':3})]!", ["Hello", TemplateVariable("WHO", type_expr="f(1,2,{'a':3})", decoder_expr="argmax", index=0), "!"])
    assert_parse("Hello[sample(n=2) WHO:f(1,2,{'a':3})]!", ["Hello", TemplateVariable("WHO", type_expr="f(1,2,{'a':3})", decoder_expr="sample(n=2)", index=0), "!"])

    # with variable decorator
    assert_parse("Hello[@stream WHO]!", ["Hello", TemplateVariable("WHO", decorator_exprs=["stream"], index=0), "!"])
    assert_parse("Hello[@chat(a=12) WHO]!", ["Hello", TemplateVariable("WHO", decorator_exprs=["chat(a=12)"], index=0), "!"])
    assert_parse("Hello[@stream @chat(a=12) WHO]!", ["Hello", TemplateVariable("WHO", decorator_exprs=["stream", "chat(a=12)"], index=0), "!"])
    assert_parse("Hello[@stream @chat(a=12) argmax WHO]!", ["Hello", TemplateVariable("WHO", decoder_expr="argmax", decorator_exprs=["stream", "chat(a=12)"], index=0), "!"])
    assert_parse("Hello[@stream @chat(a=12) argmax(n=1) WHO]!", ["Hello", TemplateVariable("WHO", decoder_expr="argmax(n=1)", decorator_exprs=["stream", "chat(a=12)"], index=0), "!"])
    assert_parse("Hello[@stream @chat(a=12) argmax(n=1) WHO: List[int]]!", ["Hello", TemplateVariable("WHO", type_expr="List[int]", decoder_expr="argmax(n=1)", decorator_exprs=["stream", "chat(a=12)"], index=0), "!"])

    assert_parse("Hello [@stream @chat(a=12) argmax(n=1) WHO: List[int]] How are you [sample TEST]!", ["Hello ", TemplateVariable("WHO", type_expr="List[int]", decoder_expr="argmax(n=1)", decorator_exprs=["stream", "chat(a=12)"], index=0), " How are you ", TemplateVariable("TEST", decoder_expr="sample", index=1), "!"])

    # with type
    assert_parse("Say 'this is a test':[RESPONSE:int]" , ["Say 'this is a test':", TemplateVariable("RESPONSE", type_expr="int", index=0)])

    # with a.b.c decorator
    assert_parse("Hello[@lmql.test WHO]!", ["Hello", TemplateVariable("WHO", decorator_exprs=["lmql.test"], index=0), "!"])


def test_functions():
    assert_parse("Hello [f(WHO)]!", ["Hello ", TemplateVariable("f(WHO)", index=0), "!"])
    assert_parse("Hello [f(WHO, 1, 'this is a test')]!", ["Hello ", TemplateVariable("f(WHO, 1, 'this is a test')", index=0), "!"])
    assert_parse("Hello [f(WHO, 1, 'this is a test'): int]!", ["Hello ", TemplateVariable("f(WHO, 1, 'this is a test')", type_expr="int", index=0), "!"])
    
    assert_parse("Hi [inline_use(REASONING, [wiki, calc])]!", ["Hi ", TemplateVariable("inline_use(REASONING, [wiki, calc])", index=0), "!"])
    
def test_newline():
    assert_parse("Say 'this is a test':[RESPONSE : test(s='[INST] foo bar baz\n> ')]", ["Say 'this is a test':", TemplateVariable("RESPONSE", type_expr="test(s='[INST] foo bar baz\n> ')", index=0)])

if __name__ == "__main__":
    run_all_tests(globals())