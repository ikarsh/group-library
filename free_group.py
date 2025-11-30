from functools import total_ordering
import itertools
from typing import (
    TYPE_CHECKING,
    Any,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

from word import Word, sign

if TYPE_CHECKING:
    from subgroup_of_free_group import SubgroupOfFreeGroup


class FreeGroup:
    def __init__(self, _gens: Tuple[str, ...] | int, name: Optional[str] = None):
        self._name = name
        if isinstance(_gens, int):
            gen_names: Tuple[str, ...] = tuple(chr(ord("a") + i) for i in range(_gens))
        else:
            gen_names = _gens
        self._gens = tuple(
            object.__new__(FreeGroupGenerator) for _ in range(len(gen_names))
        )
        for _letter, _name in zip(self._gens, gen_names):
            _letter.__init__(self, _name)

    def gens(self) -> Tuple["FreeGroupGenerator", ...]:
        return self._gens

    def __repr__(self):
        return (
            f"Free Group over {', '.join(repr(gen) for gen in self._gens)}"
            if self._name is None
            else self._name
        )

    def __hash__(self):
        return hash(("Free Group", tuple((gen.name for gen in self._gens))))

    def identity(self):
        return FreeGroupElement(self)

    def rank(self):
        return len(self.gens())

    def __iter__(
        self, *, max_len: Optional[int] = None
    ) -> Iterator["FreeGroupElement"]:
        # Iterates over the words in the group, up to a certain length.
        def paths(w: FreeGroupElement, len: int) -> Iterator[FreeGroupElement]:
            if len == 0:
                yield w
            else:
                for gen in self.gens():
                    if w.last_letter_with_sign() != (gen, -1):
                        yield from paths(w * gen, len - 1)
                    if w.last_letter_with_sign() != (gen, 1):
                        yield from paths(w * ~gen, len - 1)

        for len in itertools.count(0):
            if max_len and len > max_len:
                break
            yield from paths(self.identity(), len)

    def subgroup(
        self, relations_: Sequence["FreeGroupElement"]
    ) -> "SubgroupOfFreeGroup":
        from subgroup_of_free_group import SubgroupOfFreeGroup

        relations: List["FreeGroupElement"] = []
        for relation in relations_:
            relations.append(relation)

        return SubgroupOfFreeGroup.from_relations(self, relations)

    def normal_subgroup(
        self, relations: Sequence["FreeGroupElement"]
    ) -> "SubgroupOfFreeGroup":
        return self.subgroup(relations).normalization_in(self)

    def full_subgroup(self) -> "SubgroupOfFreeGroup":
        return self.subgroup([gen for gen in self.gens()])

    def empty_subgroup(self) -> "SubgroupOfFreeGroup":
        return self.subgroup([])

    def join_subgroups(
        self, subgroups: Sequence["SubgroupOfFreeGroup"]
    ) -> "SubgroupOfFreeGroup":
        from subgroup_of_free_group import SubgroupOfFreeGroup

        return SubgroupOfFreeGroup.join_subgroups(self, subgroups)
        # return SubgroupOfFreeGroup.from_relations(
        #     self, [gen for subgroup in subgroups for gen in subgroup.gens()]
        # )

    def intersect_subgroups(
        self, subgroups: Sequence["SubgroupOfFreeGroup"]
    ) -> "SubgroupOfFreeGroup":
        from subgroup_of_free_group import SubgroupOfFreeGroup

        return SubgroupOfFreeGroup.intersect_subgroups(self, subgroups)


@total_ordering
class FreeGroupElement(Word["FreeGroupGenerator"]):
    def __init__(self, free_group: FreeGroup):
        self.free_group = free_group
        super().__init__()

    def identity(self) -> "FreeGroupElement":
        # Overrides Word.identity, to make sure computations return the correct type.
        return FreeGroupElement(self.free_group)

    def add(self, let: "FreeGroupGenerator", pow: int = 1):
        if not let in self.free_group.gens():
            raise ValueError(f"Generator {let} not in free group {self.free_group}")
        super().add(let, pow)

    def lexicographically_lt(self, other: "FreeGroupElement") -> bool:
        if not self.free_group == other.free_group:
            raise ValueError("Cannot compare elements from different free groups.")
        n = min(len(self.word), len(other.word))
        for i in range(n):
            (let1, pow1), (let2, pow2) = self.word[i], other.word[i]
            if let1 == let2:
                if pow1 == pow2:
                    continue
                if sign(pow1) != sign(pow2):
                    return pow1 > 0 and pow2 < 0  # `a` < `a^-1`
                pow1, pow2 = abs(pow1), abs(pow2)

                if pow2 < pow1:
                    if len(other.word) == i:
                        return False
                    return let1 < other.word[i + 1][0]
                else:
                    if len(self.word) == i:
                        return True
                    return self.word[i + 1][0] < let2
            return let1 < let2
        return len(self.word) < len(other.word)

    # This is measured by the length, then lexicographically by the generator names. `a` is smaller than `a^-1`.
    def __lt__(self, other: "FreeGroupElement") -> bool:
        if self.length() == other.length():
            return self.lexicographically_lt(other)
        return self.length() < other.length()

    if TYPE_CHECKING:

        def __mul__(self, other: Word["FreeGroupGenerator"]) -> "FreeGroupElement": ...
        def __pow__(self, n: int) -> "FreeGroupElement": ...
        def __invert__(self) -> "FreeGroupElement": ...
        def copy(self) -> "FreeGroupElement": ...
        def conjugate(
            self, other: "Word[FreeGroupGenerator]"
        ) -> "FreeGroupElement": ...

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FreeGroupElement):
            return False
        return self.free_group == other.free_group and self.word == other.word

    # def __hash__(self) -> int:
    #     return hash((self.free_group, tuple(self.word)))

    def substitute(
        self, codomain: FreeGroup, values: Tuple["FreeGroupElement", ...]
    ) -> "FreeGroupElement":
        if not all(val.free_group == codomain for val in values):
            raise ValueError("Values must be from the same free group as the codomain.")
        if len(values) != self.free_group.rank():
            raise ValueError(f"Incorrect number of arguments")

        mapping = {gen: val for gen, val in zip(self.free_group.gens(), values)}
        res = codomain.identity()
        for gen, pow in self:
            res *= mapping[gen] ** pow
        return res


class FreeGroupGenerator(FreeGroupElement):
    def __init__(self, free_group: FreeGroup, name: str):
        for gen in free_group.gens():
            if self is gen:
                break
        else:
            raise ValueError(f"Generator {name} not in free group {free_group}")
        self.name = name

        super().__init__(free_group)
        self.add(self)

    def __eq__(self, other: "FreeGroupGenerator | FreeGroupElement") -> bool:
        if isinstance(other, FreeGroupGenerator):
            return self is other
        return super().__eq__(other)

    def __lt__(self, other: "FreeGroupGenerator | FreeGroupElement") -> bool:
        if isinstance(other, FreeGroupGenerator):
            return self.name < other.name
        return super().__lt__(other)

    def __hash__(self):
        return hash((self.free_group, self.name))

    def __repr__(self):
        return self.name


if TYPE_CHECKING:

    def commutator(a: FreeGroupElement, b: FreeGroupElement) -> FreeGroupElement: ...

else:
    from word import commutator
