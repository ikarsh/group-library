from typing import TYPE_CHECKING, Any, List

from free_group import FreeGroupElement, commutator as free_group_commutator
from subgroup_of_free_group import SubgroupOfFreeGroup
from utils import instance_cache


if TYPE_CHECKING:

    def isprime(n: int) -> bool: ...
    def lcm(l: List[int]) -> int: ...

else:
    from sympy import isprime, lcm


class FiniteGroup:
    def __init__(
        self, lift_group: SubgroupOfFreeGroup, kernel: SubgroupOfFreeGroup, code: str
    ):
        if code != "from SubgroupOfFreeGroup __rdiv__":
            raise ValueError(
                "FiniteGroup must be created via SubgroupOfFreeGroup.__rdiv__"
            )

        self.lift_group = lift_group
        self.kernel = kernel
        self.free_group = lift_group.free_group

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FiniteGroup):
            return False
        return self.lift_group == other.lift_group and self.kernel == other.kernel

    @instance_cache
    def order(self) -> int:
        return self.kernel.index_in(self.lift_group)

    @instance_cache
    def gens(self) -> List["FiniteGroupElement"]:
        gens: List["FiniteGroupElement"] = []
        for gen in self.lift_group.gens():
            gens.append(FiniteGroupElement(self, gen))
        return gens

    @instance_cache
    def elements(self) -> List["FiniteGroupElement"]:
        elems: List["FiniteGroupElement"] = []
        for rep in self.kernel.right_coset_representatives_in(self.lift_group):
            elems.append(FiniteGroupElement(self, rep))
        return elems

    def subgroup(self, relations: List["FiniteGroupElement"]) -> "FiniteGroup":
        for rel in relations:
            if rel.group != self:
                raise ValueError("All relations must be from the same group.")
        lifted_relations = [rel.rep for rel in relations]
        for gen in self.kernel.gens():
            lifted_relations.append(gen)

        lifted_subgroup = self.free_group.subgroup(lifted_relations)
        return lifted_subgroup / self.kernel

    def identity(self) -> "FiniteGroupElement":
        return FiniteGroupElement(self, self.free_group.identity())

    @instance_cache
    def contains_subgroup(self, other: "FiniteGroup") -> bool:
        return (
            self.lift_group.contains_subgroup(other.lift_group)
            and other.kernel == self.kernel
        )

    @instance_cache
    def is_normal_in(self, other: "FiniteGroup") -> bool:
        if not other.contains_subgroup(self):
            return False
        return self.lift_group.is_normal_in(other.lift_group)

    @instance_cache
    def normalization_in(self, other: "FiniteGroup") -> "FiniteGroup":
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")
        norm_lift = self.lift_group.normalization_in(other.lift_group)
        return norm_lift / self.kernel

    def __truediv__(self, other: "FiniteGroup") -> "FiniteGroup":
        if not self.contains_subgroup(other):
            raise ValueError("The other group must be contained in this group.")
        if not other.is_normal_in(self):
            raise ValueError("The other group must be normal in this group.")
        return self.lift_group / other.lift_group

    @instance_cache
    def index_in(self, other: "FiniteGroup") -> int:
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")
        return self.lift_group.index_in(other.lift_group)

    @instance_cache
    def center(self) -> "FiniteGroup":
        elements: List[FiniteGroupElement] = []
        for g in self.elements():
            if all(g * h == h * g for h in self.gens()):
                elements.append(g)
        return self.subgroup(elements)

    @instance_cache
    def core_in(self, other: "FiniteGroup") -> "FiniteGroup":
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")
        core_lift = self.lift_group.core_in(other.lift_group)
        assert core_lift.contains_subgroup(self.kernel)
        return core_lift / self.kernel

    @instance_cache
    def centralizer_in(self, other: "FiniteGroup") -> "FiniteGroup":
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")

        elements: List[FiniteGroupElement] = []
        for g in other.elements():
            if all(
                self.kernel.contains_element(free_group_commutator(g.rep, h.rep))
                for h in self.gens()
            ):
                elements.append(FiniteGroupElement(other, g.rep))

        return other.subgroup(elements)

    @instance_cache
    def normalizer_in(self, other: "FiniteGroup") -> "FiniteGroup":
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")

        elements: List[FiniteGroupElement] = []
        for g in other.elements():
            if all(
                self.lift_group.contains_element(free_group_commutator(g.rep, h.rep))
                for h in self.gens()
            ):
                elements.append(FiniteGroupElement(other, g.rep))

        return other.subgroup(elements)

    @instance_cache
    def derived_subgroup(self) -> "FiniteGroup":
        # We can take [gen, elem] by the identity
        # c(x * y, z) == c(x, c(y, z)) * c(y, z) * c(x, z)
        # might be possible to optimize this further
        return self.subgroup(
            [commutator(a, b) for a in self.gens() for b in self.elements()]
        )

    @instance_cache
    def is_solvable(self) -> bool:
        current_group = self
        while current_group.order() > 1:
            derived = current_group.derived_subgroup()
            if derived == current_group:
                return False
            current_group = derived
        return True

    @instance_cache
    def is_nilpotent(self) -> bool:
        current_group = self
        while current_group.order() > 1:
            center = current_group.center()
            if center.is_trivial():
                return False
            current_group = current_group / center
        return True

    @instance_cache
    def is_abelian(self) -> bool:
        return all(
            commutator(a, b) == self.identity()
            for a in self.gens()
            for b in self.gens()
        )

    @instance_cache
    def is_trivial(self) -> bool:
        return self.order() == 1

    @instance_cache
    def is_cyclic(self) -> bool:
        if lcm([g.order() for g in self.gens()]) != self.order():
            return False
        # TODO optimize
        return any(g.order() == self.order() for g in self.elements())

    @instance_cache
    def is_simple(self) -> bool:
        if self.is_trivial():
            return False

        if self.is_cyclic() and isprime(self.order()):
            return True

        checked: List[FiniteGroupElement] = []
        for g in self.elements():
            p = g.order()
            if not isprime(p):
                continue
            if g in checked:
                continue
            if self.subgroup([g]).normalization_in(self) != self:
                return False
            # Add all powers and conjugations
            for i in range(1, p):
                for elm in self.elements():
                    _g = (g**i).conjugate(elm)
                    if _g not in checked:
                        checked.append(_g)
        return True

    def p_order_element(self, p: int) -> "FiniteGroupElement":
        if not isprime(p):
            raise ValueError("p must be a prime number.")
        if not self.order() % p == 0:
            raise ValueError("The group order must be divisible by p.")
        for g in self.elements():
            if g.order() % p == 0:
                return g ** (g.order() // p)
        assert False, "Should never reach here."

    def p_sylow_subgroup(self, p: int) -> "FiniteGroup":
        if not isprime(p):
            raise ValueError("p must be a prime number.")

        curr_subgroup = self.subgroup([])
        while (self.order() // curr_subgroup.order()) % p == 0:
            g = FiniteGroupElement(
                self,
                (curr_subgroup.normalizer_in(self) / curr_subgroup)
                .p_order_element(p)
                .rep,
            )
            curr_subgroup = self.subgroup(
                [FiniteGroupElement(self, _g.rep) for _g in curr_subgroup.gens()] + [g]
            )
        return curr_subgroup


def commutator(
    a: "FiniteGroupElement", b: "FiniteGroupElement"
) -> "FiniteGroupElement":
    return a * b * ~a * ~b


class FiniteGroupElement:
    def __init__(self, group: FiniteGroup, representative: "FreeGroupElement"):
        if not group.lift_group.contains_element(representative):
            raise ValueError("The representative must be an element of the lift group.")
        self.group = group
        _, self.rep = group.kernel.express_with_right_coset_representative(
            representative
        )

    def __mul__(self, other: "FiniteGroupElement") -> "FiniteGroupElement":
        if not self.group == other.group:
            raise ValueError("Cannot multiply elements from different groups.")
        return FiniteGroupElement(self.group, self.rep * other.rep)

    def __invert__(self) -> "FiniteGroupElement":
        return FiniteGroupElement(self.group, ~self.rep)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FiniteGroupElement):
            return False
        return self.group == other.group and self.rep == other.rep

    def __pow__(self, n: int) -> "FiniteGroupElement":
        return FiniteGroupElement(self.group, self.rep**n)

    def order(self) -> int:
        e = self.group.identity()
        current = self
        order = 1
        while current != e:
            current *= self
            order += 1
        return order

    def conjugate(self, other: "FiniteGroupElement") -> "FiniteGroupElement":
        return FiniteGroupElement(self.group, self.rep.conjugate(other.rep))

    def conjugates(self) -> List["FiniteGroupElement"]:
        return [self.conjugate(g) for g in self.group.elements()]

    def __hash__(self):
        return hash((self.group, self.rep))
