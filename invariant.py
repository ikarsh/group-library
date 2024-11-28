import itertools
from typing import List, Tuple
from free_group import (
    FreeGroup,
    FreeGroupElement,
    commutator,
)
from subgroup_of_free_group import SubgroupOfFreeGroup


def invariant(H: SubgroupOfFreeGroup):
    N = H.normalization()
    return N.rank() - N.index() * N.free_group.rank()


def C(n: int) -> SubgroupOfFreeGroup:
    F = FreeGroup(("a",))
    (a,) = F.gens()
    return F.subgroup([a**n])


def prod(gps: List[SubgroupOfFreeGroup]) -> SubgroupOfFreeGroup:
    F = FreeGroup(
        tuple(f"a{i}_{j}" for i in range(len(gps)) for j in range(gps[i].rank()))
    )
    relations: List[FreeGroupElement] = []

    def gens(i: int) -> Tuple[FreeGroupElement, ...]:
        return tuple(
            FreeGroupElement.from_str(F, f"a{i}_{j}") for j in range(gps[i].rank())
        )

    for i, gp in enumerate(gps):
        for gen in gp.gens():
            relations.append(gen.substitute(F, gens(i)))

    for (i, gpi), (j, gpj) in itertools.combinations(enumerate(gps), 2):
        for geni in gpi.free_group.gens():
            for genj in gpj.free_group.gens():
                relations.append(
                    commutator(geni.substitute(F, gens(i)), genj.substitute(F, gens(j)))
                )

    return F.subgroup(relations)


def D(n: int) -> SubgroupOfFreeGroup:
    F = FreeGroup(("a", "b"))
    a, b = F.gens()
    return F.subgroup([a**n, b**2, a.conjugate(b) * a])


def Q8() -> SubgroupOfFreeGroup:
    F = FreeGroup(("a", "b"))
    a, b = F.gens()
    return F.subgroup([a**4, a ** (-2) * b**2, a * b * a * ~b])


def S(n: int) -> SubgroupOfFreeGroup:
    F = FreeGroup(("a", "b"))
    a, b = F.gens()
    return F.subgroup(
        [a**2, b**n, (a * b) ** (n - 1), commutator(a, b) ** 3]
        + [commutator(a, b**k) ** 2 for k in range(2, n // 2 + 1)]
    )
