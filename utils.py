from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Concatenate,
    Dict,
    Literal,
    Optional,
    ParamSpec,
    Tuple,
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
    purestaticmethod = staticmethod[P, R]
else:

    class classonlymethod(classmethod):

        def __get__(self, obj, cls=None):
            if obj is not None or cls is None:
                raise TypeError("Cannot call class-only method on instance")
            return super().__get__(obj, cls)
            # # Bind the class as first argument
            # def bound(*args: P.args, **kwargs: P.kwargs) -> R:
            #     return self.func(cls, *args, **kwargs)

            # return bound

    class purestaticmethod(staticmethod):
        def __get__(self, obj, cls=None):
            if obj is not None:
                raise TypeError("Cannot call class-only static method on instance")
            return super().__get__(obj, cls)
            # return self.func


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


# def id_cache(func: Callable[P, R]) -> Callable[P, R]:
#     cache: Dict[Tuple[int, ...], R] = {}

#     def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
#         key = tuple(id(a) for a in args) + (-1,) + tuple(id((k, v)) for k, v in kwargs.items())
#         if key not in cache:
#             cache[key] = func(*args, **kwargs)
#         return cache[key]

#     setattr(wrapper, "_id_cache", cache)

#     return wrapper


import weakref
from functools import wraps


def _make_ref(obj: Any) -> Callable[[], Any]:
    try:
        return weakref.ref(obj)
    except TypeError:
        return lambda: obj


Slf = TypeVar("Slf")

# P = ParamSpec("P")


def instance_cache(
    method: Callable[Concatenate[Slf, P], R],
) -> Callable[Concatenate[Slf, P], R]:
    name = f"_cached_{method.__name__}"

    @wraps(method)
    def wrapper(self: Slf, *args: P.args, **kwargs: P.kwargs) -> R:
        try:
            cache = getattr(self, name)
        except AttributeError:
            cache: Dict[Tuple[int, ...], Tuple[Tuple[Callable[[], Any], ...], R]] = {}
            setattr(self, name, cache)

        key = tuple(id(a) for a in args)
        if key in cache:
            refs, result = cache[key]
            if all(r() is a for r, a in zip(refs, args)):
                return result

        result = method(self, *args, **kwargs)
        refs = tuple(_make_ref(a) for a in args) + tuple(
            _make_ref(v) for v in kwargs.values()
        )
        cache[key] = (refs, result)
        return result

    return wrapper


def is_power_of(n: int, base: int) -> bool:
    if not (n > 0 and base > 1):
        raise ValueError("n must be positive and base must be greater than 1.")
    while n % base == 0:
        n //= base
    return n == 1
