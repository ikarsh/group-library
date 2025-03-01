from typing import TYPE_CHECKING, Literal, Optional, Tuple, overload
from free_group import FreeGroup, FreeGroupElement, FreeGroupGenerator
from utils import classonlymethod
from word import Word


class FreeGroupHomomorphism:
    def __init__(
        self,
        domain: FreeGroup,
        codomain: FreeGroup,
        map: Tuple[FreeGroupElement, ...],
    ) -> None:
        self.domain = domain
        self.codomain = codomain

        if not (
            len(map) == len(domain.gens())
            and all(x.free_group == codomain for x in map)
        ):
            raise ValueError("Invalid map")

        self.map = map

    def __call__(self, x: FreeGroupElement) -> FreeGroupElement:
        if x.free_group != self.domain:
            raise ValueError("Element not in domain")

        return x.substitute(self.codomain, self.map)

    def __repr__(self) -> str:
        return f"{self.domain} -> {self.codomain} given by {self.map}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FreeGroupHomomorphism):
            return NotImplemented

        return (
            self.domain == other.domain
            and self.codomain == other.codomain
            and self.map == other.map
        )

    def __hash__(self) -> int:
        return hash((self.domain, self.codomain, self.map))

    def __mul__(self, other: "FreeGroupHomomorphism") -> "FreeGroupHomomorphism":
        if self.codomain != other.domain:
            raise ValueError("Incompatible homomorphisms")

        new_map = tuple(x.substitute(other.codomain, other.map) for x in self.map)

        if isinstance(self, ElementaryAutomorphism) and isinstance(
            other, ElementaryAutomorphism
        ):
            return ElementaryAutomorphism(
                self.domain, self.word * other.word, new_map, _verify=False
            )

        if isinstance(self, FreeGroupEndomorphism) and isinstance(
            other, FreeGroupEndomorphism
        ):
            return FreeGroupEndomorphism(self.domain, new_map)

        return FreeGroupHomomorphism(self.domain, other.codomain, new_map)

    @classonlymethod
    def identity(cls, domain: FreeGroup) -> "FreeGroupEndomorphism":
        return FreeGroupEndomorphism(domain, tuple(domain.gens()))


class FreeGroupEndomorphism(FreeGroupHomomorphism):
    def __init__(self, domain: FreeGroup, map: Tuple[FreeGroupElement, ...]) -> None:
        super().__init__(domain, domain, map)

    if TYPE_CHECKING:

        @overload
        def __mul__(
            self, other: "FreeGroupEndomorphism"
        ) -> "FreeGroupEndomorphism": ...
        @overload
        def __mul__(
            self, other: "FreeGroupHomomorphism"
        ) -> "FreeGroupHomomorphism": ...
        def __mul__(
            self, other: "FreeGroupHomomorphism"
        ) -> "FreeGroupHomomorphism": ...

    def __pow__(self, n: int) -> "FreeGroupEndomorphism":
        if n == 0:
            return FreeGroupEndomorphism.identity(self.domain)

        if n < 0:
            raise ValueError("Negative powers not supported")

        hf = self ** (n // 2)
        if n % 2 == 0:
            return hf * hf
        else:
            return self * hf * hf


class ElementaryAutomorphism(FreeGroupEndomorphism):
    def __init__(
        self,
        domain: FreeGroup,
        word: Word["ElementaryAutomorphismGenerator"],
        map: Optional[Tuple[FreeGroupElement, ...]] = None,
        _verify: bool = True,
    ):
        self.word = word
        if map is None:
            _verify = False
            x = FreeGroupEndomorphism.identity(domain)
            for let, pow in word:
                x *= let**pow
            map = x.map
        super().__init__(domain, map)

        if _verify:
            x = FreeGroupEndomorphism.identity(domain)
            for let, pow in word:
                x *= let**pow
            assert map == x.map

    if TYPE_CHECKING:

        @overload
        def __mul__(
            self, other: "ElementaryAutomorphism"
        ) -> "ElementaryAutomorphism": ...
        @overload
        def __mul__(self, other: FreeGroupEndomorphism) -> FreeGroupEndomorphism: ...

        @overload
        def __mul__(self, other: FreeGroupHomomorphism) -> FreeGroupHomomorphism: ...

        def __mul__(self, other: FreeGroupHomomorphism) -> FreeGroupHomomorphism: ...

    # @overload
    # def __mul__(self, other: "ElementaryAutomorphism") -> "ElementaryAutomorphism": ...
    # @overload
    # def __mul__(self, other: FreeGroupEndomorphism) -> FreeGroupEndomorphism: ...
    # @overload
    # def __mul__(self, other: FreeGroupHomomorphism) -> FreeGroupHomomorphism: ...

    # def __mul__(self, other: FreeGroupHomomorphism) -> FreeGroupHomomorphism:
    #     if not isinstance(other, ElementaryAutomorphism):
    #         return NotImplemented

    #     return super().__mul__(other)

    # __mul__, __pow__, identity, __repr__


class ElementaryAutomorphismGenerator(ElementaryAutomorphism):
    def __init__(
        self,
        domain: FreeGroup,
        target: FreeGroupGenerator,
        multiplier: FreeGroupGenerator,
        direction: Literal[1, -1],
    ):
        self.word = Word([(self, 1)])


#     def __init__(
#         self,
#         domain: FreeGroup,
#         source: FreeGroupGenerator,
#         multiplier: FreeGroupGenerator,
#     ) -> None:
#         super().__init__(domain, codomain, (codomain.gen(i),))
