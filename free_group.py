from functools import total_ordering
import itertools
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
)

if TYPE_CHECKING:
    from subgroup_of_free_group import SubgroupOfFreeGroup


def sign(n: int) -> Literal[-1, 1]:
    if n < 0:
        return -1
    if n > 0:
        return 1
    raise ValueError(f"Sign of 0 is undefined")


class _Letter:
    def __init__(self, name: str):
        if not name.isidentifier():
            raise ValueError(f"Invalid generator name: {name}")
        self.name = name

    def __hash__(self):
        return hash((self.name))

    def __eq__(self, value: object) -> bool:
        return isinstance(value, _Letter) and self.name == value.name

    def __repr__(self):
        return self.name


class FreeGroup:
    def __init__(self, _letters: Tuple[str, ...] | int, name: Optional[str] = None):
        if isinstance(_letters, int):
            if _letters <= 26:
                _letters = tuple(chr(ord("a") + i) for i in range(_letters))
            else:
                raise NotImplementedError("Too many generators")
        letters = tuple(_Letter(_letter) for _letter in _letters)
        for letter0, letter1 in itertools.combinations(letters, 2):
            if letter0.name.startswith(letter1.name) or letter1.name.startswith(
                letter0.name
            ):
                raise ValueError(
                    f"Generators cannot be prefixes of each other: {letter0}, {letter1}"
                )
        self.letters = letters  # TODO hide
        self._name = name

    def gens(self) -> Tuple["FreeGroupGenerator", ...]:
        return tuple(FreeGroupGenerator(self, letter) for letter in self.letters)

    def __repr__(self):
        return (
            f"Free Group over {', '.join(repr(letter) for letter in self.letters)}"
            if self._name is None
            else self._name
        )

    def __hash__(self):
        return hash((self.letters))

    def identity(self):
        return FreeGroupElement(self, [])

    def rank(self):
        return len(self.gens())

    def __iter__(self, max_len: Optional[int] = None) -> Iterator["FreeGroupElement"]:
        def paths(w: FreeGroupElement, len: int) -> Iterator[FreeGroupElement]:
            if len == 0:
                yield w
            else:
                for gen in self.gens():
                    if not (
                        w.word and w.word[-1][0] == gen.letter and w.word[-1][1] < 0
                    ):
                        yield from paths(w * gen, len - 1)
                    if not (
                        w.word and w.word[-1][0] == gen.letter and w.word[-1][1] > 0
                    ):
                        yield from paths(w * ~gen, len - 1)

        for len in itertools.count(0):
            if max_len and len > max_len:
                break
            yield from paths(self.identity(), len)

    def subgroup(
        self, relations_: Sequence["FreeGroupElement | str"]
    ) -> "SubgroupOfFreeGroup":
        from subgroup_of_free_group import SubgroupOfFreeGroup

        relations: List["FreeGroupElement"] = []
        for relation in relations_:
            if isinstance(relation, str):
                relation = FreeGroupElement.from_str(self, relation)
            relations.append(relation)

        return SubgroupOfFreeGroup.from_relations(self, relations)

    def normal_subgroup(
        self, relations: Sequence["FreeGroupElement | str"]
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


class FreeGroupTemplate:
    def __init__(self, free_group: FreeGroup):
        self.free_group = free_group


A = TypeVar("A", bound=FreeGroupTemplate)
B = TypeVar("B", bound=FreeGroupTemplate)
C = TypeVar("C")


def verify(f: Callable[[A, B], C]) -> Callable[[A, B], C]:
    def wrapper(a: A, b: B):
        if a.free_group != b.free_group:
            raise ValueError(
                f"Cannot operate on elements from different free groups: {a.free_group}, {b.free_group}"
            )
        return f(a, b)

    return wrapper


@total_ordering
class FreeGroupElement(FreeGroupTemplate):
    # Words should always be reduced.
    # This is not enforced in the constructor, so it should not be called outside of this class.
    def __init__(self, free_group: FreeGroup, word: List[Tuple[_Letter, int]]):
        for letter, _power in word:
            if letter not in free_group.letters:
                raise ValueError(f"{letter} not a generator of {free_group}")

        self.word = word
        super().__init__(free_group)

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

    def length(self) -> int:
        return sum((abs(power) for (_let, power) in self.word))

    def copy(self) -> "FreeGroupElement":
        return FreeGroupElement(self.free_group, self.word.copy())

    def __repr__(self) -> str:
        if self.is_identity():
            return "identity"
        return "".join(
            [
                let.name + ("^" + str(pow) if pow != 1 else "")
                for (let, pow) in self.word
            ]
        )

    @verify
    def lexicographically_lt(self, other: "FreeGroupElement") -> bool:
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
                    return let1.name < other.word[i + 1][0].name
                else:
                    if len(self.word) == i:
                        return True
                    return self.word[i + 1][0].name < let2.name
            return let1.name < let2.name
        return len(self.word) < len(other.word)

    # This is measured by the length, then lexicographically by the generator names. `a` is smaller than `a^-1`.
    @verify
    def __lt__(self, other: "FreeGroupElement") -> bool:
        if self.length() == other.length():
            return self.lexicographically_lt(other)
        return self.length() < other.length()

    def is_identity(self) -> bool:
        return not self.word

    @classmethod
    def from_str(cls, free_group: FreeGroup, s_: str) -> "FreeGroupElement":
        word: List[Tuple[_Letter, int]] = []
        s = s_.replace(" ", "")
        while s:
            for let in free_group.letters:
                if s.startswith(let.name):
                    s = s[len(let.name) :]
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

                    if word and word[-1][0] == let:
                        raise ValueError(f"{s_} was given in non-reduced form.")
                    assert power != 0

                    word.append((let, power))
                    break
            else:
                raise ValueError(f"Invalid generator in {s_}")

        return FreeGroupElement(free_group, word)

    @verify
    def __mul__(self, other: "FreeGroupElement") -> "FreeGroupElement":
        res = self.copy()
        res *= other
        return res

    @verify
    def __imul__(self, other: "FreeGroupElement") -> "FreeGroupElement":
        for let, pow in other.word:
            if self.word and self.word[-1][0] == let:
                self.word[-1] = (let, self.word[-1][1] + pow)
                if self.word[-1][1] == 0:
                    self.word.pop()
            else:
                self.word.append((let, pow))
        return self

    def __invert__(self) -> "FreeGroupElement":
        return FreeGroupElement(
            self.free_group, [(let, -power) for (let, power) in self.word[::-1]]
        )

    def __pow__(self, n: int) -> "FreeGroupElement":
        if n == 0:
            return self.free_group.identity()
        elif n < 0:
            return ~(self**-n)
        else:
            half_power = self ** (n // 2)
            if n % 2 == 0:
                return half_power * half_power
            else:
                return half_power * half_power * self

    @verify
    def conjugate(self, other: "FreeGroupElement") -> "FreeGroupElement":
        return other * self * ~other

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
    def __init__(self, free_group: FreeGroup, letter: _Letter):
        if not letter in free_group.letters:
            raise ValueError(f"Generator {letter} not in free group {free_group}")
        self.letter = letter
        super().__init__(free_group, [(letter, 1)])

    def __repr__(self):
        return repr(self.letter)


@verify
def commutator(
    a: "FreeGroupElement",
    b: "FreeGroupElement",
) -> "FreeGroupElement":
    return a * b * ~a * ~b
