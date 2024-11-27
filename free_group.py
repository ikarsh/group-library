import itertools
from typing import TYPE_CHECKING, Any, Iterator, List, Literal, Sequence, Tuple

if TYPE_CHECKING:
    from subgroup_of_free_group import SubgroupOfFreeGroup


def sign(n: int) -> Literal[-1, 1]:
    if n < 0:
        return -1
    if n > 0:
        return 1
    raise ValueError(f"Sign of 0 is undefined")


class Letter:
    def __init__(self, name: str):
        if not (name and name[0].isalpha() and name.isalnum()):
            raise ValueError(f"Invalid generator name: {name}")
        self.name = name

    def __hash__(self):
        return hash((self.name))

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Letter) and self.name == value.name

    def __repr__(self):
        return self.name


class FreeGroup:
    def __init__(self, _letters: Tuple[str, ...]):
        letters = tuple(Letter(_letter) for _letter in _letters)
        for letter0, letter1 in itertools.combinations(letters, 2):
            if letter0.name.startswith(letter1.name) or letter1.name.startswith(
                letter0.name
            ):
                raise ValueError(
                    f"Generators cannot be prefixes of each other: {letter0}, {letter1}"
                )
        self.letters = letters

    def gens(self) -> Tuple["FreeGroupGenerator", ...]:
        return tuple(FreeGroupGenerator(self, letter) for letter in self.letters)

    def __repr__(self):
        return f"FreeGroup({self.letters})"

    def __hash__(self):
        return hash((self.letters))

    def identity(self):
        return FreeGroupElement(self, [])

    def subgroup(
        self, relations_: Sequence["FreeGroupElement | str"]
    ) -> "SubgroupOfFreeGroup":
        from subgroup_of_free_group import SubgroupOfFreeGroup

        relations: List["FreeGroupElement"] = []
        for relation in relations_:
            if isinstance(relation, str):
                relation = FreeGroupElement.from_str(self, relation)
            relations.append(relation)

        return SubgroupOfFreeGroup(self, relations)


class FreeGroupElement:
    # Words should always be reduced.
    # This is not enforced in the constructor, so it should not be called outside of this class.
    def __init__(self, free_group: FreeGroup, word: List[Tuple[Letter, int]]):
        for letter, _power in word:
            if letter not in free_group.letters:
                raise ValueError(f"{letter} not a generator of {free_group}")

        self.free_group = free_group
        self.word = word

    def __iter__(self) -> Iterator[Tuple[Letter, int]]:
        return iter(self.word)

    def __hash__(self) -> int:
        return hash((self.free_group, self.word))

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

    # Lexicographical order
    def __le__(self, other: "FreeGroupElement") -> bool:
        if self.free_group != other.free_group:
            raise ValueError(
                f"Cannot compare elements from different free groups: {self.free_group}, {other.free_group}"
            )
        n = min(len(self.word), len(other.word))
        for i in range(n):
            (let1, pow1), (let2, pow2) = self.word[i], other.word[i]
            if let1 == let2:
                if pow1 == pow2:
                    continue
                if sign(pow1) != sign(pow2):
                    return pow1 > 0 and pow2 < 0  # We prefer `a` over `a^-1`
                pow1, pow2 = abs(pow1), abs(pow2)

                if pow2 < pow1:
                    if len(other.word) == i:
                        return False
                    return let1.name <= other.word[i][0].name
                else:
                    if len(self.word) == i:
                        return True
                    return self.word[i][0].name <= let2.name
            return let1.name <= let2.name
        return len(self.word) <= len(other.word)

    def is_identity(self) -> bool:
        return not self.word

    @classmethod
    def from_str(cls, free_group: FreeGroup, s_: str) -> "FreeGroupElement":
        word: List[Tuple[Letter, int]] = []
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

    def __mul__(self, other: "FreeGroupElement") -> "FreeGroupElement":
        res = self.copy()
        res *= other
        return res

    def __imul__(self, other: "FreeGroupElement") -> "FreeGroupElement":
        if self.free_group != other.free_group:
            raise ValueError(
                f"Cannot multiply elements from different free groups: {self.free_group}, {other.free_group}"
            )

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
            self.free_group, [(gen, -power) for (gen, power) in self.word[::-1]]
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

    def conjugate(self, other: "FreeGroupElement") -> "FreeGroupElement":
        if self.free_group != other.free_group:
            raise ValueError(
                f"Cannot conjugate elements from different free groups: {self.free_group}, {other.free_group}"
            )
        return other * self * ~other


class FreeGroupGenerator(FreeGroupElement):
    def __init__(self, free_group: FreeGroup, letter: Letter):
        if not letter in free_group.letters:
            raise ValueError(f"Generator {letter} not in free group {free_group}")
        self.letter = letter
        super().__init__(free_group, [(letter, 1)])

    def __repr__(self):
        return repr(self.letter)


def commutator(
    a: "FreeGroupElement",
    b: "FreeGroupElement",
) -> "FreeGroupElement":
    if a.free_group != b.free_group:
        raise ValueError(
            f"Cannot compute commutator of elements from different free groups: {a.free_group}, {b.free_group}"
        )
    return a * b * ~a * ~b
