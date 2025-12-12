import random
from typing import TYPE_CHECKING, Any, List

from free_group import FreeGroupElement
from subgroup_of_free_group import SubgroupOfFreeGroup
from utils import instance_cache, is_power_of


if TYPE_CHECKING:

    def isprime(n: int) -> bool: ...
    def lcm(l: List[int]) -> int: ...

else:
    from sympy import isprime, lcm


class FiniteGroup:
    def __init__(
        self, *, lift_group: SubgroupOfFreeGroup, kernel: SubgroupOfFreeGroup, code: str
    ):
        if code != "verified normal and finite index":
            raise ValueError()

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
            gens.append(
                FiniteGroupElement(
                    self.kernel, gen, code="I promise element normalizes kernel"
                )
            )
        return gens

    @instance_cache
    def elements(self) -> List["FiniteGroupElement"]:
        elems: List["FiniteGroupElement"] = []
        for rep in self.kernel.right_coset_representatives_in(self.lift_group):
            elems.append(
                FiniteGroupElement(
                    self.kernel, rep, code="I promise element normalizes kernel"
                )
            )
        return elems

    def contains_element(self, element: "FiniteGroupElement") -> bool:
        if element.kernel != self.kernel:
            raise TypeError()
        return self.lift_group.contains_element(element.rep)

    def with_added_elements(
        self, elements: List["FiniteGroupElement"]
    ) -> "FiniteGroup":
        for elem in elements:
            if elem.kernel != self.kernel:
                raise ValueError("All elements must be from the same group.")
        return FiniteGroup(
            lift_group=self.lift_group.with_added_elements(
                [elem.rep for elem in elements]
            ),
            kernel=self.kernel,
            code="verified normal and finite index",
        )

    def subgroup(self, generators: List["FiniteGroupElement"]) -> "FiniteGroup":
        for gen in generators:
            if not self.contains_element(gen):
                raise ValueError("All generators must be from the group.")
        return FiniteGroup(
            lift_group=self.kernel.with_added_elements(
                [elem.rep for elem in generators]
            ),
            kernel=self.kernel,
            code="verified normal and finite index",
        )

    def identity(self) -> "FiniteGroupElement":
        return FiniteGroupElement(
            self.kernel,
            self.free_group.identity(),
            code="I promise element normalizes kernel",
        )

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
        return FiniteGroup(
            lift_group=norm_lift,
            kernel=self.kernel,
            code="verified normal and finite index",
        )

    def __truediv__(self, other: "FiniteGroup") -> "FiniteGroup":
        if not self.contains_subgroup(other):
            raise ValueError("The other group must be contained in this group.")
        if not other.is_normal_in(self):
            raise ValueError("The other group must be normal in this group.")
        return FiniteGroup(
            lift_group=self.lift_group,
            kernel=other.lift_group,
            code="verified normal and finite index",
        )

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
        return FiniteGroup(
            lift_group=core_lift,
            kernel=self.kernel,
            code="verified normal and finite index",
        )

    @instance_cache
    def centralizer_in(self, other: "FiniteGroup") -> "FiniteGroup":
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")

        return other.subgroup(
            [
                g
                for g in other.elements()
                if all(commutator(g, h) == other.identity() for h in self.gens())
            ]
        )

    def conjugate(self, g: "FiniteGroupElement") -> "FiniteGroup":
        if not self.kernel == g.kernel:
            raise TypeError()

        return FiniteGroup(
            lift_group=self.lift_group.conjugate(g.rep),
            kernel=self.kernel,
            code="verified normal and finite index",
        )

    def right_coset_representatives_in(
        self, other: "FiniteGroup"
    ) -> List["FiniteGroupElement"]:
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")

        return [
            FiniteGroupElement(
                other.kernel, rep, code="I promise element normalizes kernel"
            )
            for rep in self.lift_group.right_coset_representatives_in(other.lift_group)
        ]

    def left_coset_representatives_in(
        self, other: "FiniteGroup"
    ) -> List["FiniteGroupElement"]:
        return [~g for g in self.right_coset_representatives_in(other)]

    @instance_cache
    def conjugates_in(self, other: "FiniteGroup") -> List["FiniteGroup"]:
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")

        conjugates: List[FiniteGroup] = []
        for g in self.left_coset_representatives_in(other):
            conj = self.conjugate(g)
            if conj not in conjugates:
                conjugates.append(conj)
        return conjugates

    @instance_cache
    def normalizer_in(self, other: "FiniteGroup") -> "FiniteGroup":
        if not other.contains_subgroup(self):
            raise ValueError("The other group must contain this group.")

        return FiniteGroup(
            lift_group=self.lift_group.normalizer_in(other.lift_group),
            kernel=self.kernel,
            code="verified normal and finite index",
        )

    def commutator_of_subgroup_with_self(
        self, subgroup: "FiniteGroup"
    ) -> "FiniteGroup":
        if not self.contains_subgroup(subgroup):
            raise ValueError("The subgroup must be contained in this group.")

        # From the relation c(x * y, z) == c(x, c(y, z)) * c(y, z) * c(x, z)
        # it follows that [G, H] is generated by all [g1, g2, ..., gk, h]
        # where the gi's run over generators of G and h runs over generators of H.

        gens = [commutator(g, h) for g in self.gens() for h in subgroup.gens()]
        current_group = self.subgroup(gens)

        while True:
            gens = [commutator(g, h) for g in self.gens() for h in gens]
            next_group = current_group.with_added_elements(gens)
            if next_group == current_group:
                return current_group
            current_group = next_group

    @instance_cache
    def derived_subgroup(self) -> "FiniteGroup":
        return self.commutator_of_subgroup_with_self(self)

    @instance_cache
    def derived_series(self) -> List["FiniteGroup"]:
        series: List["FiniteGroup"] = [self]
        current_group = self
        while current_group.order() > 1:
            derived = current_group.derived_subgroup()
            if derived == current_group:
                break
            series.append(derived)
            current_group = derived
        return series

    @instance_cache
    def is_solvable(self) -> bool:
        return self.derived_series()[-1].is_trivial()

    @instance_cache
    def derived_length(self) -> int:
        if not self.is_solvable():
            raise ValueError("The group is not solvable.")
        return len(self.derived_series()) - 1

    @instance_cache
    def abelianization(self) -> "FiniteGroup":
        return self / self.derived_subgroup()

    @instance_cache
    def lower_central_series(self) -> List["FiniteGroup"]:
        series: List["FiniteGroup"] = [self]
        current_group = self
        while current_group.order() > 1:
            next_group = self.commutator_of_subgroup_with_self(current_group)
            if next_group == current_group:
                break
            series.append(next_group)
            current_group = next_group
        return series

    @instance_cache
    def is_nilpotent(self) -> bool:
        return self.lower_central_series()[-1].is_trivial()

    @instance_cache
    def nilpotency_class(self) -> int:
        if not self.is_nilpotent():
            raise ValueError("The group is not nilpotent.")
        return len(self.lower_central_series()) - 1

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

    # TODO optimize
    @instance_cache
    def sylow_subgroup(self, p: int) -> "FiniteGroup":
        if not isprime(p):
            raise ValueError("p must be a prime number.")

        p_elements = [g for g in self.elements() if is_power_of(g.order(), p)]
        curr_subgroup = self.subgroup([])

        while (self.order() // curr_subgroup.order()) % p == 0:
            g = random.choice(p_elements)
            if curr_subgroup.contains_element(g):
                continue
            while not curr_subgroup.contains_element(g**p):
                g = g**p
            if curr_subgroup.conjugate(g) != curr_subgroup:
                continue
            curr_subgroup = curr_subgroup.with_added_elements([g])
        return curr_subgroup


def commutator(
    a: "FiniteGroupElement", b: "FiniteGroupElement"
) -> "FiniteGroupElement":
    return a * b * ~a * ~b


class FiniteGroupElement:
    def __init__(
        self,
        kernel: "SubgroupOfFreeGroup",
        elem: "FreeGroupElement",
        code: str,
    ):
        if code != "I promise element normalizes kernel":
            if not kernel.conjugate(elem) == kernel:
                raise ValueError("Element must normalize the kernel.")
        self.kernel = kernel
        self.rep = kernel.walk_commensurable_word(elem)

    def __mul__(self, other: "FiniteGroupElement") -> "FiniteGroupElement":
        if not self.kernel == other.kernel:
            raise ValueError("Cannot multiply elements from different groups.")
        return FiniteGroupElement(
            self.kernel,
            self.rep * other.rep,
            code="I promise element normalizes kernel",
        )

    def __invert__(self) -> "FiniteGroupElement":
        return FiniteGroupElement(
            self.kernel, ~self.rep, code="I promise element normalizes kernel"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FiniteGroupElement):
            return False
        return self.kernel == other.kernel and self.rep == other.rep

    def __pow__(self, n: int) -> "FiniteGroupElement":
        return FiniteGroupElement(
            self.kernel, self.rep**n, code="I promise element normalizes kernel"
        )

    def is_trivial(self) -> bool:
        return self.kernel.contains_element(self.rep)

    @instance_cache
    # TODO optimize
    def order(self) -> int:
        current = self
        order = 1
        while not current.is_trivial():
            current *= self
            order += 1
        return order

    def conjugate(self, other: "FiniteGroupElement") -> "FiniteGroupElement":
        return other * self * ~other

    def __hash__(self):
        return hash((self.kernel, self.rep))

    def lift_to(self, G: FiniteGroup) -> "FiniteGroupElement":
        if not self.kernel.contains_subgroup(G.kernel):
            raise ValueError(
                "The kernel of the target group must be contained in the kernel of this element's group."
            )
        if not G.kernel.conjugate(self.rep) == G.kernel:
            raise ValueError("The element does not normalize the target kernel.")
        return FiniteGroupElement(
            G.kernel, self.rep, code="I promise element normalizes kernel"
        )
