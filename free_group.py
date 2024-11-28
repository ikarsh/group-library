from functools import total_ordering
import itertools
from typing import (
    TYPE_CHECKING,
    Any,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
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


@total_ordering
class Word:
    # Words should always be reduced.
    # Do not access the __init__ directly, only through the identity method.
    def __init__(self):
        self.word: List[Tuple[_Letter, int]] = []

    def identity(self) -> "Word":
        return Word()

    def add(self, let: _Letter, pow: int = 1):
        if self.word and self.word[-1][0] == let:
            self.word[-1] = (let, self.word[-1][1] + pow)
            if self.word[-1][1] == 0:
                self.word.pop()
        else:
            self.word.append((let, pow))

    def remove(self, let: _Letter):
        self.add(let, -1)

    def __imul__(self, other: "Word"):
        for let, pow in other.word:
            self.add(let, pow)
        return self

    def __mul__(self, other: "Word") -> "Word":
        res = self.copy()
        res *= other
        return res

    def __pow__(self, n: int) -> "Word":
        if n == 0:
            return self.identity()
        elif n < 0:
            return ~(self**-n)
        else:
            half_power = self ** (n // 2)
            if n % 2 == 0:
                return half_power * half_power
            else:
                return half_power * half_power * self

    def __invert__(self) -> "Word":
        res = self.identity()
        for let, pow in self.word[::-1]:
            res.add(let, -pow)
        return res

    def copy(self) -> "Word":
        res = self.identity()
        for let, pow in self.word:
            res.add(let, pow)
        return res

    def __repr__(self) -> str:
        if self.is_identity():
            return "identity"
        return "".join(
            [
                let.name + ("^" + str(pow) if pow != 1 else "")
                for (let, pow) in self.word
            ]
        )

    def is_identity(self):
        return not self.word

    def length(self) -> int:
        return sum((abs(power) for (_let, power) in self.word))

    def last_letter_with_sign(self) -> Optional[Tuple[_Letter, int]]:
        if self.is_identity():
            return None
        let, pow = self.word[-1]
        return (let, sign(pow))

    def last_letter(self) -> Optional[_Letter]:
        if self.is_identity():
            return None
        return self.word[-1][0]

    def lexicographically_lt(self, other: "Word") -> bool:
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
    def __lt__(self, other: "Word") -> bool:
        if self.length() == other.length():
            return self.lexicographically_lt(other)
        return self.length() < other.length()

    def from_str_over_letters(self, letters: Tuple[_Letter, ...], s_: str) -> "Word":
        for l0, l1 in itertools.combinations(letters, 2):
            if l0.name.startswith(l1.name) or l1.name.startswith(l0.name):
                raise ValueError(
                    f"letters cannot be prefixes of each other: {l0}, {l1}"
                )

        word = self.identity()
        s = s_.replace(" ", "")
        while s:
            for let in letters:
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

                    if word.last_letter() == let:
                        raise ValueError(f"{s_} was given in non-reduced form.")
                    assert power != 0

                    word.add(let, power)
                    break
            else:
                raise ValueError(f"Invalid generator in {s_}")

        return word

    def conjugate(self, other: "Word") -> "Word":
        return self.identity() * other * self * ~other


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
        return FreeGroupElement(self)

    def rank(self):
        return len(self.gens())

    def __iter__(self, max_len: Optional[int] = None) -> Iterator["FreeGroupElement"]:
        def paths(w: FreeGroupElement, len: int) -> Iterator[FreeGroupElement]:
            if len == 0:
                yield w
            else:
                for gen in self.gens():
                    if w.last_letter_with_sign() != (gen.letter, -1):
                        yield from paths(w * gen, len - 1)
                    if w.last_letter_with_sign() != (gen.letter, 1):
                        yield from paths(w * ~gen, len - 1)

        for len in itertools.count(0):
            if max_len and len > max_len:
                break
            yield from paths(self.identity(), len)

    def elem_from_str(self, s: str) -> "FreeGroupElement":
        return self.identity() * self.identity().from_str_over_letters(self.letters, s)

    def subgroup(
        self, relations_: Sequence["FreeGroupElement | str"]
    ) -> "SubgroupOfFreeGroup":
        from subgroup_of_free_group import SubgroupOfFreeGroup

        relations: List["FreeGroupElement"] = []
        for relation in relations_:
            if isinstance(relation, str):
                relation = self.elem_from_str(relation)
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


# A = TypeVar("A", bound=FreeGroupTemplate)
# B = TypeVar("B", bound=FreeGroupTemplate)
# C = TypeVar("C")


# def verify(f: Callable[[A, B], C]) -> Callable[[A, B], C]:
#     def wrapper(a: A, b: B):
#         if a.free_group != b.free_group:
#             raise ValueError(
#                 f"Cannot operate on elements from different free groups: {a.free_group}, {b.free_group}"
#             )
#         return f(a, b)

#     return wrapper


@total_ordering
class FreeGroupElement(Word):
    def __init__(self, free_group: FreeGroup):
        self.free_group = free_group
        super().__init__()

    def identity(self) -> "FreeGroupElement":
        return FreeGroupElement(self.free_group)

    def add(self, let: _Letter, pow: int = 1):
        if not let in self.free_group.letters:
            raise ValueError(f"Generator {let} not in free group {self.free_group}")
        super().add(let, pow)

    if TYPE_CHECKING:

        def __mul__(self, other: Word) -> "FreeGroupElement": ...
        def __pow__(self, n: int) -> "FreeGroupElement": ...
        def __invert__(self) -> "FreeGroupElement": ...
        def copy(self) -> "FreeGroupElement": ...
        def conjugate(self, other: Word) -> "FreeGroupElement": ...

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
    def __init__(self, free_group: FreeGroup, letter: _Letter):
        if not letter in free_group.letters:
            raise ValueError(f"Generator {letter} not in free group {free_group}")
        self.letter = letter

        super().__init__(free_group)
        self.add(letter)


def commutator(
    a: "FreeGroupElement",
    b: "FreeGroupElement",
) -> "FreeGroupElement":
    return a * b * ~a * ~b
