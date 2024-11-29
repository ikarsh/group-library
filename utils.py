from typing import (
    Any,
    Callable,
    Concatenate,
    Generic,
    Literal,
    Optional,
    ParamSpec,
    Type,
    TypeVar,
)


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


# def classonlymethod(f: Callable[P, R]) -> Callable[P, R]:
#     def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
#         if not args:
#             assert False, "Should not happen"
#         if isinstance(args[0], type):
#             raise TypeError(f"{args[0]} is not a class")
#         return f(*args, **kwargs)

#     return wrap

# F = TypeVar("F", bound=Callable[..., Any])


def panic() -> Any:
    assert False


P = ParamSpec("P")
R = TypeVar("R")


class classonlymethod(Generic[P, R]):
    def __init__(self, func: Callable[Concatenate[Any, P], R]) -> None:
        self.func = func

    def __get__(self, obj: Any, cls: Type[Any] | None) -> Callable[P, R]:
        if obj is not None or cls is None:
            raise TypeError("Cannot call class-only method on instance")

        # Bind the class as first argument
        def bound(*args: P.args, **kwargs: P.kwargs) -> R:
            return self.func(cls, *args, **kwargs)

        return bound
