from typing import Generic, Iterator, TypeVar, List, Optional, Tuple

from utils import sign

T = TypeVar("T")



class Word(Generic[T]):
    # Words should always be reduced.

    # Do not access the __init__ directly, only through the identity method.
    # That way, when applied to subclasses, the correct type is returned.
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

    def __itruediv__(self, other: "Word[T]"):
        # To avoid creating the ~other object.
        for let, pow in other.word[::-1]:
            self.add(let, -pow)
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

    def __iter__(self) -> Iterator[Tuple[T, int]]:
        return iter(self.word)

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

    def conjugate(self, other: "Word[T]") -> "Word[T]":
        # To avoid creating the partial words separately.
        res = self.identity()
        res *= other
        res *= self
        res /= other
        return res


def commutator(a: Word[T], b: Word[T]) -> Word[T]:
    # To avoid creating the partial words separately.
    res = a.identity()
    res *= a
    res *= b
    res /= a
    res /= b
    return res
