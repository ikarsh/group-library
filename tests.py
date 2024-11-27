from free_group import FreeGroup, commutator


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
    assert (x * y).conjugate(z) == x.conjugate(z) * y.conjugate(z)
    assert x.conjugate(e) == x
    assert x.conjugate(y * z) == x.conjugate(z).conjugate(y)

    assert commutator(x, y) == x * y * ~x * ~y
    assert commutator(x, y) == ~commutator(y, x)
    assert commutator(x * y, z) == commutator(x, commutator(y, z)) * commutator(
        y, z
    ) * commutator(x, z)


def test_subgroup_of_free_group():
    F = FreeGroup(("a", "b"))
    a, b = F.gens()

    lst = [
        [(a * b) ** 10, commutator(a, b) ** 3, b**1, b.conjugate(a)],
        [a**2, b**3, commutator(a, b)],
        [a**2 * b**3 * a ** (-2), b**3, commutator(a, b.conjugate(a**5))],
    ]

    for gens in lst:
        free_gens = F.subgroup(gens).free_gens
        assert len(free_gens) <= len(gens)
