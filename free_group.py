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

from word import Word

if TYPE_CHECKING:
    from subgroup_of_free_group import SubgroupOfFreeGroup


class FreeGroup:
    def __init__(self, _letters: Tuple[str, ...] | int, name: Optional[str] = None):
        if isinstance(_letters, int):
            if _letters <= 26:
                letters: Tuple[str, ...] = tuple(
                    chr(ord("a") + i) for i in range(_letters)
                )
            else:
                raise NotImplementedError("Too many generators")
        else:
            letters = _letters
        for letter0, letter1 in itertools.combinations(letters, 2):
            if letter0.startswith(letter1) or letter1.startswith(letter0):
                raise ValueError(
                    f"Generators cannot be prefixes of each other: {letter0}, {letter1}"
                )
        self._letters = letters  # TODO hide
        self._name = name

    def contains_letter(self, letter: str) -> bool:
        return letter in self._letters

    def gens(self) -> Tuple["FreeGroupGenerator", ...]:
        return tuple(FreeGroupGenerator(self, letter) for letter in self._letters)

    def __repr__(self):
        return (
            f"Free Group over {', '.join(repr(letter) for letter in self._letters)}"
            if self._name is None
            else self._name
        )

    def __hash__(self):
        return hash((self._letters))

    def identity(self):
        return FreeGroupElement(self)

    def rank(self):
        return len(self.gens())

    def __iter__(self, max_len: Optional[int] = None) -> Iterator["FreeGroupElement"]:
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

    def elem_from_str(self, s: str) -> "FreeGroupElement":
        return self.identity() * self.identity().from_str_over_letters(self._letters, s)

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
        return self.subgroup(relations).normalization()

    def full_subgroup(self) -> "SubgroupOfFreeGroup":
        return self.subgroup([gen for gen in self.gens()])

    def empty_subgroup(self) -> "SubgroupOfFreeGroup":
        return self.subgroup([])

    def join_subgroups(
        self, subgroups: Sequence["SubgroupOfFreeGroup"]
    ) -> "SubgroupOfFreeGroup":
        from subgroup_of_free_group import SubgroupOfFreeGroup

        return SubgroupOfFreeGroup.from_relations(
            self, [gen for subgroup in subgroups for gen in subgroup.gens()]
        )


@total_ordering
class FreeGroupElement(Word[str]):
    def __init__(self, free_group: FreeGroup):
        self.free_group = free_group
        super().__init__()

    def identity(self) -> "FreeGroupElement":
        return FreeGroupElement(self.free_group)

    def add(self, let: str, pow: int = 1):
        if not self.free_group.contains_letter(let):
            raise ValueError(f"Generator {let} not in free group {self.free_group}")
        super().add(let, pow)

    if TYPE_CHECKING:

        def __mul__(self, other: Word[str]) -> "FreeGroupElement": ...
        def __pow__(self, n: int) -> "FreeGroupElement": ...
        def __invert__(self) -> "FreeGroupElement": ...
        def copy(self) -> "FreeGroupElement": ...
        def conjugate(self, other: Word[str]) -> "FreeGroupElement": ...

    def __iter__(self) -> Iterator[Tuple["FreeGroupGenerator", int]]:
        return iter(
            (FreeGroupGenerator(self.free_group, let), pow) for let, pow in self.word
        )

    def __hash__(self) -> int:
        return hash((self.free_group, tuple(self.word)))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FreeGroupElement):
            return False
        return self.free_group == other.free_group and self.word == other.word

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
    def __init__(self, free_group: FreeGroup, letter: str):
        if not free_group.contains_letter(letter):
            raise ValueError(f"Generator {letter} not in free group {free_group}")
        self.letter = letter

        super().__init__(free_group)
        self.add(letter)


def commutator(
    a: "FreeGroupElement",
    b: "FreeGroupElement",
) -> "FreeGroupElement":
    return a * b * ~a * ~b
