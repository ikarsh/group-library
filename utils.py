from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Concatenate,
    Dict,
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


def panic() -> Any:
    assert False


P = ParamSpec("P")
R = TypeVar("R")

if TYPE_CHECKING:
    classonlymethod = classmethod[T, P, R]
else:

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


S = TypeVar("S", bound="Cached")


class Cached:
    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def do_cached_method(self: S, method: Callable[[S], R]) -> R:
        result: Optional[R] = self._cache.get(method.__name__)
        if result is not None:
            return result
        result = method(self)
        self._cache[method.__name__] = result
        return result

    def flush(self):
        self._cache.clear()


def cached_value(func: Callable[[S], R]) -> Callable[[S], R]:
    @wraps(func)
    def wrap(self: S) -> R:
        return self.do_cached_method(func)

    return wrap
