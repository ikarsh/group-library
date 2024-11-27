from typing import List
from free_group import FreeGroup, FreeGroupElement, commutator


def test_free_group():
    F = FreeGroup(("a", "b", "c"))
    a, b, c = F.gens()
    x = a * b * ~a * b * c**2
    y = b ** (-3) * c * a * b
    z = a * b * c
    e = F.identity()

    assert x * e == e * x == x
    assert x * ~x == ~x * x == e
    assert (x * y) * z == x * (y * z)
    assert (x * y) ** (-1) == y ** (-1) * x ** (-1)

    assert x**5 == x * x * x * x * x

    assert x.conjugate(y) == y * x * ~y
    assert x.conjugate(e) == x
    assert e.conjugate(x) == e
    assert (x * y).conjugate(z) == x.conjugate(z) * y.conjugate(z)
    assert x.conjugate(y * z) == x.conjugate(z).conjugate(y)

    c = commutator
    assert c(x, y) == x * y * ~x * ~y
    assert c(x, y) == ~c(y, x)
    assert c(x * y, z) == c(x, c(y, z)) * c(y, z) * c(x, z)
    assert (
        c(z.conjugate(y), c(x, y))
        * c(y.conjugate(x), c(z, x))
        * c(x.conjugate(z), c(y, z))
        == e
    )  # Jacobi identity


def test_subgroup_of_free_group():
    F = FreeGroup(("a", "b"))
    a, b = F.gens()

    lst: List[List[FreeGroupElement]] = [
        [a, b],
        [a, b ** (-10)],
        [a * b, b * a],
        [(a * b) ** 2, a],
        [(a * b) ** 3, b],
        [a**2, b**3, commutator(a, b)],
        [(a * b) ** 10, commutator(a, b) ** 3, b**1, b.conjugate(a)],
        [a**2 * b**3 * a ** (-2), b**3, commutator(a, b.conjugate(a**5))],
    ]

    for gens in lst:
        H = F.subgroup(gens)
        free_gens = H.gens()
        assert len(free_gens) <= len(gens)
        for gen in gens:
            word = H.express(gen)
            assert word is not None
            for g, _ in word:
                assert g in free_gens

            w = F.identity()
            for g, n in word:
                w *= g**n
            assert w == gen
