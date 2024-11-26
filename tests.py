from free_group import FreeGroup, FreeGroupElement


def test_free_group():
    F = FreeGroup(("a", "b", "c"))
    a, b, c = F.gens
    x = ~a * a
    x = a**2
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
    assert FreeGroupElement.commutator(x, y) == x * y * ~x * ~y
