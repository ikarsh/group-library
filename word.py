from typing import Literal
from functools import total_ordering
import itertools
from typing import (
    List,
    Literal,
    Optional,
    Tuple,
)


def sign(n: int) -> Literal[-1, 1]:
    if n < 0:
        return -1
    if n > 0:
        return 1
    raise ValueError(f"Sign of 0 is undefined")


class Letter:
    def __init__(self, name: str):
        if not name.isidentifier():
            raise ValueError(f"Invalid generator name: {name}")
        self.name = name

    def __hash__(self):
        return hash((self.name))

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Letter) and self.name == value.name

    def __repr__(self):
        return self.name


@total_ordering
class Word:
    # Words should always be reduced.
    # Do not access the __init__ directly, only through the identity method.
    def __init__(self):
        self.word: List[Tuple[Letter, int]] = []

    def identity(self) -> "Word":
        return Word()

    def add(self, let: Letter, pow: int = 1):
        if self.word and self.word[-1][0] == let:
            self.word[-1] = (let, self.word[-1][1] + pow)
            if self.word[-1][1] == 0:
                self.word.pop()
        else:
            self.word.append((let, pow))

    def remove(self, let: Letter):
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

    def last_letter_with_sign(self) -> Optional[Tuple[Letter, int]]:
        if self.is_identity():
            return None
        let, pow = self.word[-1]
        return (let, sign(pow))

    def last_letter(self) -> Optional[Letter]:
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

    def from_str_over_letters(self, letters: Tuple[Letter, ...], s_: str) -> "Word":
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


def commutator(a: Word, b: Word) -> Word:
    return a * b * ~a * ~b
