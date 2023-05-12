from lmql.ops import FollowMap, fmap

def test_overlapping_product():
    f1 = fmap(
        ("a", 1),
        ("b", 2),
        ("*", 3),
    )
    f2 = fmap(
        ("b", 1),
        ("c", 2),
        ("*", 3),
    )

    # print(f1.product(f2))
    assert f1.product(f2) == fmap(
        ("a", (1,3)),
        ("b", (2,1)),
        ("c", (3,2)),
        ("*", (3,3))
    )

def test_disjunct_product():
    f1 = fmap()
    f2 = fmap()

    assert str(f1.product(f2)) == "∅"

def test_disjunct_product2():
    f1 = fmap()
    f2 = fmap(
        ("a", "abc")
    )

    assert str(f1.product(f2)) == "∅"

def test_disjunct_product3():
    f1 = fmap(
        ("b", "bcd")
    )
    f2 = fmap(
        ("a", "abc"),
        ("*", "fallback")
    )

    assert f1.product(f2) == fmap(
        ("b", ("bcd", "fallback"))
    )

def test_simple_case():
    f1 = fmap(
        ("a", True),
        ("b", False)
    )
    f2 = fmap(
        ("a", True),
        ("b", False)
    )

    assert f1.product(f2) == fmap(
        ("a", (True, True)),
        ("b", (False, False)),
    )

def test_three_operands():
    f1 = fmap(
        ("a", True),
        ("b", False)
    )
    f2 = fmap(
        ("a", True),
        ("b", False)
    )
    f3 = fmap(
        ("a", True),
        ("b", False)
    )

    assert f1.product(f2, f3) == fmap(
        ("a", (True, True, True)),
        ("b", (False, False, False)),
    )

if __name__ == "__main__":
    test_overlapping_product()
    test_disjunct_product()
    test_disjunct_product2()
    test_disjunct_product3()
    test_simple_case()
    test_three_operands()