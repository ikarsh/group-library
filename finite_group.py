from typing import List
from free_group import FreeGroupElement
from subgroup_of_free_group import NormalFiniteIndexSubgroupOfFreeGroup

# from utils import Cached, cached_value


class FiniteGroup:
    def __init__(self, kernel: NormalFiniteIndexSubgroupOfFreeGroup):
        self.kernel = kernel
        self.free_group = kernel.free_group

    # @cached_value
    def order(self) -> int:
        return self.kernel.index()

    def gens(self) -> List["FiniteGroupElement"]:
        gens: List["FiniteGroupElement"] = []
        for gen in self.free_group.gens():
            gens.append(FiniteGroupElement(self, gen))
        return gens

    def elements(self) -> List["FiniteGroupElement"]:
        elems: List["FiniteGroupElement"] = []
        for rep in self.kernel.right_coset_representatives():
            elems.append(FiniteGroupElement(self, rep))
        return elems

    def center_size(self) -> int:
        elements = self.elements()
        center_elems = [g for g in elements if all(g * h == h * g for h in self.gens())]
        return len(center_elems)


class FiniteGroupElement:
    def __init__(self, group: FiniteGroup, representative: "FreeGroupElement"):
        self.group = group
        _, self.rep = group.kernel.express_with_right_coset_representative(
            representative
        )

    def identity(self) -> "FiniteGroupElement":
        return FiniteGroupElement(self.group, self.group.free_group.identity())

    def __mul__(self, other: "FiniteGroupElement") -> "FiniteGroupElement":
        assert self.group == other.group
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
        e = self.identity()
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
