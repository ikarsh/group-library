import itertools
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Tuple

if TYPE_CHECKING:
    from subgroup_of_free_group import SubgroupOfFreeGroup


class FreeGroup:
    def __init__(self, gen_names: Tuple[str, ...], name: Optional[str] = None):
        gens = tuple(FreeGroupGenerator(self, gen_name) for gen_name in gen_names)
        for gen0, gen1 in itertools.combinations(gens, 2):
            if gen0.name.startswith(gen1.name) or gen1.name.startswith(gen0.name):
                raise ValueError(
                    f"Generators cannot be prefixes of each other: {gen0}, {gen1}"
                )
        self.gen_names = gen_names
        self.gens = gens
        self.name = name

    def __repr__(self):
        return f"FreeGroup({self.gens})" if self.name is None else self.name

    def __hash__(self):
        return hash((self.name, self.gen_names))

    def identity(self):
        return FreeGroupElement(self, [])

    def subgroup(
        self, relations_: List["FreeGroupGenerator | FreeGroupElement | str"]
    ) -> "SubgroupOfFreeGroup":
        from subgroup_of_free_group import SubgroupOfFreeGroup

        relations: List["FreeGroupElement"] = []
        for relation in relations_:
            if isinstance(relation, FreeGroupGenerator):
                relation = relation.as_group_element()
            elif isinstance(relation, str):
                relation = FreeGroupElement.from_str(self, relation)
            assert isinstance(relation, FreeGroupElement)
            relations.append(relation)

        return SubgroupOfFreeGroup(self, relations)


class FreeGroupGenerator:
    def __init__(self, free_group: FreeGroup, name: str):
        if not (name and name[0].isalpha() and name.isalnum()):
            raise ValueError(f"Invalid generator name: {name}")
        self.free_group = free_group
        self.name = name

    def __hash__(self):
        return hash((self.free_group, self.name))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, FreeGroupGenerator):
            return super().__eq__(other)
        return self.as_group_element() == other

    def __repr__(self):
        return self.name

    def as_group_element(self):
        return FreeGroupElement(self.free_group, [(self, 1)])

    def __invert__(self) -> "FreeGroupElement":
        return ~self.as_group_element()

    def __mul__(
        self, other: "FreeGroupGenerator | FreeGroupElement"
    ) -> "FreeGroupElement":
        return self.as_group_element() * other

    def __pow__(self, n: int) -> "FreeGroupElement":
        return self.as_group_element() ** n

    def conjugate(
        self, other: "FreeGroupGenerator | FreeGroupElement"
    ) -> "FreeGroupElement":
        return self.as_group_element().conjugate(other)


class FreeGroupElement:
    def __init__(
        self, free_group: FreeGroup, word: List[Tuple[FreeGroupGenerator, int]]
    ):
        for gen, _power in word:
            if gen not in free_group.gens:
                raise ValueError(f"Generator {gen} not in free group {free_group}")

        self.free_group = free_group
        self.word = word

    def __iter__(self) -> Iterator[Tuple[FreeGroupGenerator, int]]:
        return iter(self.word)

    def __hash__(self) -> int:
        return hash((self.free_group, tuple(self.reduce().word)))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, FreeGroupGenerator):
            other = other.as_group_element()
        if not isinstance(other, FreeGroupElement):
            return False
        return self.free_group == other.free_group and self.word == other.word

    def __repr__(self) -> str:
        if self.is_identity():
            return "identity"
        return "".join(
            [
                gen.name + ("^" + str(power) if power != 1 else "")
                for (gen, power) in self.word
            ]
        )

    def is_identity(self) -> bool:
        return not self.word

    @classmethod
    def from_str(cls, free_group: FreeGroup, s_: str) -> "FreeGroupElement":
        word: List[Tuple[FreeGroupGenerator, int]] = []
        s = s_.replace(" ", "")
        while s:
            for gen in free_group.gens:
                if s.startswith(gen.name):
                    s = s[len(gen.name) :]
                    if s.startswith("^"):
                        s = s[1:]
                        power = 0
                        sign = 1
                        if s.startswith("-"):
                            s = s[1:]
                            sign = -1
                        if not s or not s[0].isdigit() or s[0] == "0":
                            raise ValueError(f"Invalid power in {s_}")
                        while s and s[0].isdigit():
                            power = 10 * power + int(s[0])
                            s = s[1:]
                        power *= sign
                    else:
                        power = 1

                    word.append((gen, power))
                    break
            else:
                raise ValueError(f"Invalid generator in {s_}")

        return FreeGroupElement(free_group, word).reduce()

    def reduce(self) -> "FreeGroupElement":
        word: List[Tuple[FreeGroupGenerator, int]] = []
        for gen, power in self.word:
            if word and word[-1][0] == gen:
                word[-1] = (gen, word[-1][1] + power)
            else:
                word.append((gen, power))
            if word and word[-1][1] == 0:
                word.pop()
        return FreeGroupElement(self.free_group, word)

    def __mul__(
        self, other: "FreeGroupGenerator | FreeGroupElement"
    ) -> "FreeGroupElement":
        if isinstance(other, FreeGroupGenerator):
            other = other.as_group_element()
        assert isinstance(other, FreeGroupElement)
        if self.free_group != other.free_group:
            raise ValueError(
                f"Cannot multiply elements from different free groups: {self.free_group}, {other.free_group}"
            )
        word = self.word.copy()
        # Reduction
        for gen, power in other.word:
            if word and word[-1][0] == gen:
                word[-1] = (gen, word[-1][1] + power)
                if word[-1][1] == 0:
                    word.pop()
            else:
                word.append((gen, power))
        return FreeGroupElement(self.free_group, word)

    def __invert__(self) -> "FreeGroupElement":
        return FreeGroupElement(
            self.free_group, [(gen, -power) for (gen, power) in self.word[::-1]]
        )

    def __pow__(self, n: int) -> "FreeGroupElement":
        if n == 0:
            return self.free_group.identity()
        elif n < 0:
            return ~(self**-n)
        else:
            half = n // 2
            half_power = self**half
            if n % 2 == 0:
                return half_power * half_power
            else:
                return half_power * half_power * self

    def conjugate(
        self, other: "FreeGroupGenerator | FreeGroupElement"
    ) -> "FreeGroupElement":
        if isinstance(other, FreeGroupGenerator):
            other = other.as_group_element()
        assert isinstance(other, FreeGroupElement)
        if self.free_group != other.free_group:
            raise ValueError(
                f"Cannot conjugate elements from different free groups: {self.free_group}, {other.free_group}"
            )
        return other * self * ~other

    @classmethod
    def commutator(
        cls,
        a: "FreeGroupGenerator | FreeGroupElement",
        b: "FreeGroupGenerator | FreeGroupElement",
    ) -> "FreeGroupElement":
        if isinstance(a, FreeGroupGenerator):
            a = a.as_group_element()
        if isinstance(b, FreeGroupGenerator):
            b = b.as_group_element()
        assert isinstance(a, FreeGroupElement) and isinstance(b, FreeGroupElement)
        if a.free_group != b.free_group:
            raise ValueError(
                f"Cannot compute commutator of elements from different free groups: {a.free_group}, {b.free_group}"
            )
        return a * b * ~a * ~b
