from typing import Generic, Literal, Protocol, TypeVar
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


# Currently these are the only allowed types for Word. This is silly.
T = TypeVar("T", str, "Word")


@total_ordering
class Word(Generic[T]):
    # Words should always be reduced.
    # Do not access the __init__ directly, only through the identity method.
    def __init__(self):
        self.word: List[Tuple[T, int]] = []

    def identity(self) -> "Word[T]":
        return Word()

    def add(self, let: T, pow: int = 1):
        if self.word and self.word[-1][0] == let:
            self.word[-1] = (let, self.word[-1][1] + pow)
            if self.word[-1][1] == 0:
                self.word.pop()
        else:
            self.word.append((let, pow))

    def remove(self, let: T):
        self.add(let, -1)

    def __imul__(self, other: "Word[T]"):
        for let, pow in other.word:
            self.add(let, pow)
        return self

    def __mul__(self, other: "Word[T]") -> "Word[T]":
        res = self.copy()
        res *= other
        return res

    def __pow__(self, n: int) -> "Word[T]":
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

    def __invert__(self) -> "Word[T]":
        res = self.identity()
        for let, pow in self.word[::-1]:
            res.add(let, -pow)
        return res

    def copy(self) -> "Word[T]":
        res = self.identity()
        for let, pow in self.word:
            res.add(let, pow)
        return res

    def __repr__(self) -> str:
        if self.is_identity():
            return "identity"
        return "".join(
            [
                repr(let) + ("^" + str(pow) if pow != 1 else "")
                for (let, pow) in self.word
            ]
        )

    def is_identity(self):
        return not self.word

    def length(self) -> int:
        return sum((abs(power) for (_let, power) in self.word))

    def last_letter_with_sign(self) -> Optional[Tuple[T, int]]:
        if self.is_identity():
            return None
        let, pow = self.word[-1]
        return (let, sign(pow))

    def last_letter(self) -> Optional[T]:
        if self.is_identity():
            return None
        return self.word[-1][0]

    def lexicographically_lt(self: "Word[T]", other: "Word[T]") -> bool:
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
    def __lt__(self: "Word[T]", other: "Word[T]") -> bool:
        if self.length() == other.length():
            return self.lexicographically_lt(other)
        return self.length() < other.length()

    @classmethod
    def from_str_over_letters(cls, letters: Tuple[str, ...], s_: str) -> "Word[str]":
        for l0, l1 in itertools.combinations(letters, 2):
            if l0.startswith(l1) or l1.startswith(l0):
                raise ValueError(
                    f"letters cannot be prefixes of each other: {l0}, {l1}"
                )

        word = Word[str]().identity()
        s = s_.replace(" ", "")
        while s:
            for let in letters:
                if s.startswith(let):
                    s = s[len(let) :]
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

    def conjugate(self, other: "Word[T]") -> "Word[T]":
        return self.identity() * other * self * ~other


def commutator(a: Word[T], b: Word[T]) -> Word[T]:
    return a * b * ~a * ~b
