from lmql.ops.token_set import *
import lmql.ops.token_set as token_set
from transformers import AutoTokenizer

def assert_equal(x, y):
    if x != y:
        raise AssertionError(f"{x} != {y}")

if __name__ == "__main__":
    """
    TODO: tests here need to be fixed (do not use set, but tset)
    """

    VocabularyMatcher.init(AutoTokenizer.from_pretrained("gpt2"))

    # print(tset("abc"))
    # print(tset("abc").mask.sum())

    # print(ntset("abc"))

    # print(tset("abc").union("*"))
    # print(tset("a"))
    # print(tset("abc").union(tset("a", "b", "c")))

    # print(tset("eos"))

    # # print(tset("[^\u0120].*", regex=True).__str__(full=True))
    # print(tset(".*\n.*", regex=True).__str__(full=True))

    # assert intersect(set(["abc"]), set(["cba"])) == "∅"
    
    # p1 = set(["a", "b"])
    # p2 = set(["b", "c"])

    # assert intersect(p1, p2) == set(["b"])

    # p1 = "*"
    # p2 = set(["b", "c"])

    # assert str(sorted(list(intersect(p1, p2)))) == "['b', 'c']"
    # assert str(sorted(list(intersect(p2, p1)))) == "['b', 'c']"

    # assert intersect(set(["abc"]), "∅") == "∅"

    # # f1 = fmap(
    # #     ("eos", True),
    # #     ("*", False)
    # # )
    # # class DummyOp:
    # #     def follow(self, v):
    # #         return "IS_TRUE" if v == True else "IS_FALSE"
    # # fm = follow_apply(f1, DummyOp())
    # # assert fm.value("eos") == "IS_TRUE"
    # # assert fm.value("something else") == "IS_FALSE"

    # # f1 = fmap(
    # #     ("eos", True),
    # #     ("*", False)
    # # )
    # # class DummyOp2:
    # #     def follow(self, v):
    # #         if v == True:
    # #             return fmap(
    # #                 ("eos", "IS_EOS_TRUE"),
    # #                 ("*", "IS_OTHER_TRUE")
    # #             )
    # #         else:
    # #             return fmap(
    # #                 ("eos", "IS_EOS_FALSE"),
    # #                 ("*", "IS_OTHER_FALSE")
    # #             )
    # # fm = follow_apply(f1, DummyOp2())

    # assert tset("b", "c").intersect(tset("a", "b")) == tset("b")
    # assert ntset("b", "c").intersect(tset("a", "b")) == tset("a")
    # assert tset("a", "b").intersect(ntset("b", "c")) == tset("a")
    # assert ntset("b", "c").intersect(ntset("a", "b")) == ntset("a", "b", "c")


    # assert tset("a", "b").intersect("*") == tset("a", "b")
    # assert_equal(tset("a", "b").intersect("∅"), "∅")
    # assert_equal(ntset("a", "b").intersect("*"), ntset("a","b"))
    # assert_equal(ntset("a", "b").intersect("∅"), "∅")

    # assert_equal(tset("a", "b").union("*"), "*")
    # assert_equal(tset("a", "b").union("∅"), tset("a", "b"))
    # assert_equal(ntset("a", "b").union("*"), "*")
    # assert_equal(ntset("a", "b").union("∅"), ntset("a", "b"))
    
    # assert tset("b", "c").union(tset("a", "b")) == tset("a", "b", "c")
    # assert tset("b", "c").union(ntset("a", "b")) == ntset("a")
    # assert ntset("b", "c").union(tset("a", "b")) == ntset("c")
    # assert ntset("b", "c").union(ntset("a", "b")) == ntset("b")