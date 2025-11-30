from typing import Any, List
from free_group import FreeGroupElement
from subgroup_of_free_group import SubgroupOfFreeGroup
from utils import purestaticmethod


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

    # @cached_value
    def order(self) -> int:
        return self.kernel.index_in(self.lift_group)

    def gens(self) -> List["FiniteGroupElement"]:
        gens: List["FiniteGroupElement"] = []
        for gen in self.lift_group.gens():
            gens.append(FiniteGroupElement(self, gen))
        return gens

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
        return FiniteGroupElement.identity(self)

    def contains_subgroup(self, other: "FiniteGroup") -> bool:
        return (
            self.lift_group.contains_subgroup(other.lift_group)
            and other.kernel == self.kernel
        )

    def is_normal_in(self, other: "FiniteGroup") -> bool:
        if not other.contains_subgroup(self):
            return False
        return self.lift_group.is_normal_in(other.lift_group)

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

    def index_in(self, other: "FiniteGroup") -> int:
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")
        return self.lift_group.index_in(other.lift_group)

    def center(self) -> "FiniteGroup":
        elements: List[FiniteGroupElement] = []
        for g in self.elements():
            if all(g * h == h * g for h in self.gens()):
                elements.append(g)
        return self.subgroup(elements)

    def core_in(self, other: "FiniteGroup") -> "FiniteGroup":
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")
        core_lift = self.lift_group.core_in(other.lift_group)
        assert core_lift.contains_subgroup(self.kernel)
        return core_lift / self.kernel

    def centralizer_in(self, other: "FiniteGroup") -> "FiniteGroup":
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")

        elements: List[FiniteGroupElement] = []
        for g in other.elements():
            if all(
                self.kernel.contains_element(commutator(g.rep, h.rep))
                for h in self.gens()
            ):
                elements.append(FiniteGroupElement(other, g.rep))

        return other.subgroup(elements)

    def normalizer_in(self, other: "FiniteGroup") -> "FiniteGroup":
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")

        elements: List[FiniteGroupElement] = []
        for g in other.elements():
            if all(
                self.lift_group.contains_element(commutator(g.rep, h.rep))
                for h in self.gens()
            ):
                elements.append(FiniteGroupElement(other, g.rep))

        return other.subgroup(elements)

def commutator(g1: FreeGroupElement, g2: FreeGroupElement) -> FreeGroupElement:
    return g1 * g2 * ~g1 * ~g2


class FiniteGroupElement:
    def __init__(self, group: FiniteGroup, representative: "FreeGroupElement"):
        if not group.lift_group.contains_element(representative):
            raise ValueError("The representative must be an element of the lift group.")
        self.group = group
        _, self.rep = group.kernel.express_with_right_coset_representative(
            representative
        )

    @purestaticmethod
    def identity(group: FiniteGroup) -> "FiniteGroupElement":
        return FiniteGroupElement(group, group.free_group.identity())

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
        e = FiniteGroupElement.identity(self.group)
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
