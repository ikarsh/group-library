import itertools
from math import factorial, prod
from typing import List
from finite_group_presentations import A, C, D, Q8, S, dir_prod
from free_group import FreeGroup, FreeGroupElement, commutator
from subgroup_of_free_group import SubgroupOfFreeGroup
from utils import unwrap


def test_free_group_identities():
    F = FreeGroup(("a", "b", "c"))
    a, b, c = F.gens()
    x, y, z = (a * b * ~a * b * c**2, b ** (-3) * c * a * b, a * b * c**5 * ~a)
    e = F.identity()

    # Group axioms
    assert x * e == e * x == x
    assert x * ~x == ~x * x == e
    assert (x * y) * z == x * (y * z)
    assert (x * y) ** (-1) == y ** (-1) * x ** (-1)

    # Exponentiation
    assert x**5 == x * x * x * x * x
    assert y ** (-2) == ~y * ~y

    # Conjugation
    assert x.conjugate(y) == y * x * ~y
    assert x.conjugate(e) == x
    assert e.conjugate(x) == e
    assert (x * y).conjugate(z) == x.conjugate(z) * y.conjugate(z)
    assert x.conjugate(y * z) == x.conjugate(z).conjugate(y)

    # Commutators
    c = commutator
    assert c(x, y) == x * y * ~x * ~y
    assert c(x, y) == ~c(y, x)
    assert c(x * y, z) == c(x, c(y, z)) * c(y, z) * c(x, z)
    assert (
        c(~x, ~y) == (~x) ** 2 * c(x, ~y) * (~y) ** 2 * c(y, x) * x**2 * c(~x, y) * y**2
    )

    # Jacobi identity
    assert (
        c(z.conjugate(y), c(x, y))
        * c(y.conjugate(x), c(z, x))
        * c(x.conjugate(z), c(y, z))
        == e
    )


def test_subgroup_creation():
    F = FreeGroup(("a", "b"))
    words = list(F.__iter__(4))
    for w1, w2 in itertools.combinations(words, 2):
        F.subgroup([w1, w2])


def test_subgroup_new_generators():
    # Tests that the subgroup manages to form a basis, that generates the original and is no longer than it.
    # TODO: Add proofs the new generators are generated by the originals.

    # I am not sure how to test that the new generators are free.
    # Technically, returning the original generators would satisfy this test...

    F = FreeGroup(("a", "b"))
    a, b = F.gens()

    lst: List[List[FreeGroupElement]] = [
        [a, b],
        [a, b ** (-10)],
        [a * b, b * a],
        [(a * b) ** 2, a],
        [(a * b) ** 3, b],
        [b * a * ~b, a**3 * ~b],
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


def test_subgroup_element_containement():
    F = FreeGroup(("a", "b"))
    a, b = F.gens()
    x, y = (a**3 * b ** (-2) * a * b**2, a * b * a * b * a * b)

    # contains_element
    assert F.full_subgroup().contains_element(a)
    assert not F.empty_subgroup().contains_element(a)
    assert F.subgroup([x, y]).contains_element(x * y * x ** (-2) * y**3)
    assert not F.subgroup([a**2, b]).contains_element(a)


def test_normal_subgroup():
    F2 = FreeGroup(("a", "b"))
    a, b = F2.gens()

    assert F2.full_subgroup().is_normal()
    assert F2.empty_subgroup().is_normal()
    assert not F2.subgroup([a]).is_normal()
    assert F2.subgroup(
        [a, a.conjugate(b), a.conjugate(b**2), a.conjugate(b**3), b**4]
    ).is_normal()

    # A subgroup of finite index which is not normal.
    H = F2.subgroup([a, b**2, (a**2).conjugate(b), b.conjugate(b * a)])
    assert H.index() == 3 and H.rank() == 4 and not H.is_normal()
    assert H == H.conjugate(a) and H != H.conjugate(b)
    assert H.normalization() == H.conjugate(b).normalization()

    # Generate S3
    assert F2.normal_subgroup([a**2, b**3, b.conjugate(a) * a]).is_normal()


def test_finite_groups():
    # This verifies the sizes of finite groups, and that the ranks of the kernels for them satisfy the formula:
    # rank(N_G) == |G| * (n - 1) + 1, where N_G = ker(F_n -> G).
    def verify_formula(N: SubgroupOfFreeGroup):
        idx = N.index()
        assert idx is not None
        assert N.rank() == idx * (N.free_group.rank() - 1) + 1

    for n in range(2, 10):
        Cn = C(n)
        assert Cn.index() == n
        verify_formula(Cn)

    for n in range(3, 10):
        Dn = D(n)
        assert Dn.index() == 2 * n
        verify_formula(Dn)

    Q = Q8()
    assert Q.index() == 8
    verify_formula(Q)

    for n in range(3, 6):
        Sn = S(n)
        assert Sn.index() == factorial(n)
        verify_formula(Sn)

    for n in range(3, 6):
        An = A(n)
        assert An.index() == factorial(n) // 2
        verify_formula(An)

    for gps in [
        [C(2), C(2)],
        [S(3), S(3)],
        [A(3), A(3), C(2)],
        [Q8(), C(2)],
    ]:
        P = dir_prod(gps)
        assert P.index() == prod((unwrap(g.index()) for g in gps))
        verify_formula(P)


def test_all():
    test_free_group_identities()
    test_subgroup_creation()
    test_subgroup_new_generators()
    test_subgroup_element_containement()
    test_normal_subgroup()
    test_finite_groups()
