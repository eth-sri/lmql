from lmql.language.qstrings import QstringParser, TemplateVariable, FExpression, DistributionVariable
from lmql.tests.expr_test_utils import run_all_tests

def assert_parse(qstring, expected, mode="all"):
    r = QstringParser(mode=mode).parse(qstring)
    assert r == expected, f"Expected {expected}, got {r}"

def test_qstrings():
    assert_parse("hello [world]", ["hello ", TemplateVariable("world")])
    assert_parse("hello [[world]]", ["hello [[world]]"])
    assert_parse("hello [[[world]]]", ["hello [[", TemplateVariable("world"), "]]"])
    assert_parse("hello [[[[world]]]]", ["hello [[[[world]]]]"])

    # with curly
    assert_parse("hello {{world}}", ["hello {{world}}"])
    assert_parse("hello {{{world}}}", ["hello {{", FExpression("world"), "}}"])
    assert_parse("hello {{{{world}}}}", ["hello {{{{world}}}}"])

    # both
    assert_parse("hello [[world]] {{world}}", ["hello [[world]] {{world}}"])
    assert_parse("hello [[world]] {{{world}}}", ["hello [[world]] {{", FExpression("world"), "}}"])
    assert_parse("hello [[world]] {{{{world}}}}", ["hello [[world]] {{{{world}}}}"])
    assert_parse("hello [world] {world} ", ["hello ", TemplateVariable("world"), " ", FExpression("world"), " "])

    # nested
    assert_parse("hello [world [[nested]]]", ["hello [world [[nested]]]"])
    assert_parse("hello [world [nested]]", ["hello [world ", TemplateVariable("nested"), "]"])
    
    # trailing/leading/dangling
    assert_parse("hello [world]]", ["hello ", TemplateVariable("world"), "]"])
    assert_parse("[[hello world]", ["[[hello world]"])
    assert_parse("[ [hello]", ["[ ", TemplateVariable("hello")])

    # square in curly
    assert_parse("hello {world [nested]}", ["hello ", FExpression("world [nested]")])
    # curly in square
    assert_parse("hello [world{nested}]", ["hello [world", FExpression("nested"), "]"])
    assert_parse("hello [world {nested}]", ["hello [world ", FExpression("nested"), "]"])


    # mode square-only
    assert_parse("hello [world]", ["hello ", TemplateVariable("world")], mode="square-only")
    assert_parse("hello {hi} [world]", ["hello {hi} ", TemplateVariable("world")], mode="square-only")

    assert_parse("hello {{world}}", ["hello {{world}}"], mode="square-only")
    assert_parse("hello {{{world}}}", ["hello {{{world}}}"], mode="square-only")
    assert_parse("hello {{{{world}}}}", ["hello {{{{world}}}}"], mode="square-only")
    assert_parse("hello [world] {world} ", ["hello ", TemplateVariable("world"), " {world} "], mode="square-only")
    assert_parse("hello {world} [world]", ["hello {world} ", TemplateVariable("world")], mode="square-only")

    # distribution variables
    assert_parse("hello [distribution:world]", ["hello ", DistributionVariable("world")])
    assert_parse("hello [distribution:world] [distribution:world]", ["hello ", DistributionVariable("world"), " ", DistributionVariable("world")])

run_all_tests(globals())