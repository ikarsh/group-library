from typing import Literal, Optional, TypeVar


def sign(n: int) -> Literal[-1, 1]:
    if n < 0:
        return -1
    if n > 0:
        return 1
    raise ValueError(f"Sign of 0 is undefined")


T = TypeVar("T")


def unwrap(x: Optional[T]) -> T:
    assert x is not None
    return x
