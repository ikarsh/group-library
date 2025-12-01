from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
)
from free_group import (
    FreeGroup,
    FreeGroupElement,
    FreeGroupGenerator,
)
from utils import Cached, cached_value, instance_cache, purestaticmethod, panic, sign
from word import Word

if TYPE_CHECKING:
    from finite_group import FiniteGroup

Sign = Literal[-1, 1]


class Vertex:
    idx = 0

    def __init__(self, elem: FreeGroupElement):
        self.elem = elem
        self.idx = Vertex.idx
        Vertex.idx += 1
        self.forward_edges: Dict[FreeGroupGenerator, Edge] = {}
        self.backward_edges: Dict[FreeGroupGenerator, Edge] = {}

    def delete(self):
        if self.forward_edges or self.backward_edges:
            raise ValueError("Cannot delete vertex with edges")

    def observe_direction(
        self, gen: FreeGroupGenerator, sign: int
    ) -> Optional[Tuple["Edge", "Vertex"]]:
        if sign == 1:
            edge = self.forward_edges.get(gen)
            if edge is None:
                return None
            return edge, edge.target
        else:
            edge = self.backward_edges.get(gen)
            if edge is None:
                return None
            return edge, edge.source

    def observe_direction_violent(
        self, gen: FreeGroupGenerator, sign: int
    ) -> Tuple["Edge", "Vertex"]:
        # If this can't find a way, it will create one.
        dir = self.observe_direction(gen, sign)
        if dir is not None:
            return dir
        if sign == 1:
            new_vertex = Vertex(self.elem * gen)
            edge = Edge(self, gen, new_vertex)
        else:
            new_vertex = Vertex(self.elem * ~gen)
            edge = Edge(new_vertex, gen, self)
        return edge, new_vertex

    def walk_edge(self, gen: FreeGroupGenerator, sign: int) -> Optional["Vertex"]:
        dir = self.observe_direction(gen, sign)
        return None if dir is None else dir[1]

    def walk_word(
        self, word: FreeGroupElement
    ) -> Optional[Tuple[List[Tuple["Edge", Sign]], "Vertex"]]:
        vertex = self
        edges: List[Tuple["Edge", Sign]] = []
        for gen, pow in word:
            s = sign(pow)
            for _ in range(abs(pow)):
                dir = vertex.observe_direction(gen, s)
                if dir is None:
                    return None
                edge, vertex = dir
                edges.append((edge, s))
        return edges, vertex

    def walk_word_violent(
        self, word: FreeGroupElement
    ) -> Tuple[List[Tuple["Edge", Sign]], "Vertex"]:
        # If this can't find a way, it will create one.
        vertex = self
        edges: List[Tuple["Edge", Sign]] = []
        for gen, pow in word:
            s = sign(pow)
            for _ in range(abs(pow)):
                edge, vertex = vertex.observe_direction_violent(gen, s)
                edges.append((edge, s))
        return edges, vertex

    def __lt__(self, other: "Vertex") -> bool:
        return self.elem < other.elem

    def __hash__(self) -> int:
        return hash(self.idx)

    def __repr__(self) -> str:
        return repr(self.elem)


class Edge:
    idx = 0

    def __init__(self, source: Vertex, elem: FreeGroupGenerator, target: Vertex):
        self.source = source
        self.elem = elem
        self.target = target
        self.idx = Edge.idx
        Edge.idx += 1

        if (
            self.source.forward_edges.get(self.elem) is not None
            or self.target.backward_edges.get(self.elem) is not None
        ):
            raise ValueError(f"This shouldn't happen.")
        self.source.forward_edges[self.elem] = self
        self.target.backward_edges[self.elem] = self

    def delete(self):
        if not (
            self.source.forward_edges.pop(self.elem) is self
            and self.target.backward_edges.pop(self.elem) is self
        ):
            raise ValueError(f"This shouldn't happen")

    def __hash__(self) -> int:
        return hash(self.idx)

    def __lt__(self, other: "Edge") -> bool:
        return (self.source, self.elem, self.target) < (
            other.source,
            other.elem,
            other.target,
        )

    def __repr__(self) -> str:
        return f"{self.source} -- {self.elem} --> {self.target}"


class SubgroupOfFreeGroup(Cached):
    # The first few methods are related to the graph representation, which is private.
    def __init__(self, free_group: FreeGroup, code: str):
        if code != "From _SubgroupOFFreeGroupBase._new":
            raise RuntimeError("Do not use this directly.")
        self.free_group = free_group
        self._identity_vertex = Vertex(free_group.identity())

        super().__init__()

    @purestaticmethod
    def _new(free_group: FreeGroup):
        return SubgroupOfFreeGroup(
            free_group, code="From _SubgroupOFFreeGroupBase._new"
        )

    @cached_value
    def _vertices(self) -> Set[Vertex]:
        res = set((self._identity_vertex,))
        unchecked = set((self._identity_vertex,))
        while unchecked:
            vertex = unchecked.pop()
            for edge in vertex.forward_edges.values():
                if not edge.target in res:
                    unchecked.add(edge.target)
                    res.add(edge.target)
            for edge in vertex.backward_edges.values():
                if not edge.source in res:
                    unchecked.add(edge.source)
                    res.add(edge.source)
        return res

    @cached_value
    def _edges(self) -> Set[Edge]:
        res: Set[Edge] = set()
        for vertex in self._vertices():
            for edge in vertex.forward_edges.values():
                res.add(edge)
        return res

    def _push_word(self, word: FreeGroupElement):
        self.flush()
        vertex = self._identity_vertex
        _edges, vertex = vertex.walk_word_violent(word)

        # Now glue vertex to the identity vertex, recursively.
        glues = [(vertex, self._identity_vertex)]

        while glues:
            v0, v1 = glues.pop()
            if v0 == v1:
                continue

            if v0.elem < v1.elem:
                v0, v1 = v1, v0

            for gen, edge in list(v0.forward_edges.items()):
                assert edge.elem == gen
                edge.delete()
                v1_next = v1.walk_edge(gen, 1)

                # Annoying edgecase
                if edge.target == v0:
                    v1_prev = v1.backward_edges.get(gen)
                    if v1_next is not None:
                        glues.append((v1, v1_next))
                    if v1_prev is not None:
                        glues.append((v1_prev.source, v1))
                    if v1_prev is None and v1_next is None:
                        Edge(v1, gen, v1)
                else:
                    if v1_next is None:
                        Edge(v1, gen, edge.target)
                    else:
                        glues.append((edge.target, v1_next))

            for gen, edge in list(v0.backward_edges.items()):
                edge.delete()
                v1_prev = v1.walk_edge(gen, -1)
                # The edgecase does not happen here.

                if v1_prev is None:
                    Edge(edge.source, gen, v1)
                else:
                    glues.append((edge.source, v1_prev))

            v0.delete()
            for i, pair in list(enumerate(glues)):
                if pair[0] == pair[1] == v0:
                    glues[i] = (v1, v1)
                elif v0 in pair:
                    other = pair[1 - pair.index(v0)]
                    glues[i] = (other, v1)

    def _relabel(self):
        # What this function actually does is give every vertex a minimal representative.
        # Minimality is taken with respect to length and then lexicographically.
        # This ensures a spanning tree is created.
        uncleared_vertices = self._vertices().copy()

        while uncleared_vertices:
            v = uncleared_vertices.pop()
            for edge in v.forward_edges.values():
                suggestion = edge.source.elem * edge.elem
                if suggestion < edge.target.elem:
                    edge.target.elem = suggestion
                    uncleared_vertices.add(edge.target)
            for edge in v.backward_edges.values():
                suggestion = edge.target.elem * ~edge.elem
                if suggestion < edge.source.elem:
                    edge.source.elem = suggestion
                    uncleared_vertices.add(edge.source)

    @cached_value
    def _cycle_generators(self) -> Dict[Edge, FreeGroupElement]:
        self._relabel()
        return {
            edge: value
            for edge in self._edges()
            if not (
                value := edge.source.elem * edge.elem * ~edge.target.elem
            ).is_identity()
        }

    @cached_value
    def gens(self) -> Tuple[FreeGroupElement, ...]:
        return tuple(self._cycle_generators().values())

    def signed_gens(self) -> List[FreeGroupElement]:
        return [g**s for g in self.gens() for s in (-1, 1)]

    def walk_commensurable_word(self, elem: FreeGroupElement):
        path = self._identity_vertex.walk_word(elem)
        if path is None:
            raise ValueError(f"The element {elem} was not commensurable")
        _edges, vertex = path
        return vertex.elem

    def express(self, elem: FreeGroupElement) -> Optional[Word[FreeGroupElement]]:
        path = self._identity_vertex.walk_word(elem)
        if path is None:
            return None
        edges, vertex = path
        if vertex != self._identity_vertex:
            return None

        word = Word[FreeGroupElement]().identity()
        for edge, sign in edges:
            gen = self._cycle_generators().get(edge)
            if gen is not None:
                word.add(gen, sign)

        return word

    def contains_element(self, elem: FreeGroupElement) -> bool:
        path = self._identity_vertex.walk_word(elem)
        if path is None:
            return False
        _edges, vertex = path
        return vertex == self._identity_vertex

    @instance_cache
    def contains_subgroup(self, other: "SubgroupOfFreeGroup") -> bool:
        for gen in other.gens():
            if not self.contains_element(gen):
                return False
        return True

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SubgroupOfFreeGroup):
            return False
        if self.free_group != other.free_group:
            return False
        return self.contains_subgroup(other) and other.contains_subgroup(self)

    def __repr__(self) -> str:
        return f"Subgroup of {self.free_group} with free basis {self.gens()}"

    @purestaticmethod
    def from_relations(
        free_group: FreeGroup, relations: List[FreeGroupElement]
    ) -> "SubgroupOfFreeGroup":
        for relation in relations:
            if relation.free_group != free_group:
                raise ValueError(f"Relation {relation} not in free group {free_group}")

        res = SubgroupOfFreeGroup._new(free_group)
        for relation in relations:
            res._push_word(relation)

        return res

    def copy(self) -> "SubgroupOfFreeGroup":
        return SubgroupOfFreeGroup.from_relations(self.free_group, list(self.gens()))

    @purestaticmethod
    def _full_subgroup(free_group: FreeGroup) -> "SubgroupOfFreeGroup":
        return SubgroupOfFreeGroup.from_relations(free_group, list(free_group.gens()))

    def conjugate(self, elem: FreeGroupElement) -> "SubgroupOfFreeGroup":
        conjugation = self.copy()
        _edges, vertex = conjugation._identity_vertex.walk_word_violent(~elem)
        conjugation._identity_vertex = vertex
        for v in conjugation._vertices():
            v.elem = elem * v.elem

        conjugation._identity_vertex.elem = self.free_group.identity()
        conjugation._relabel()
        return conjugation

    def is_empty(self) -> bool:
        return len(self._vertices()) == 1 and len(self._edges()) == 0

    @instance_cache
    def has_finite_index_in(self, other: "SubgroupOfFreeGroup | FreeGroup") -> bool:
        if isinstance(other, FreeGroup):
            other = SubgroupOfFreeGroup._full_subgroup(other)
        if self.free_group != other.free_group:
            raise ValueError("Cannot compare subgroups of different free groups.")
        if not other.contains_subgroup(self):
            raise ValueError("The other subgroup must contain this subgroup.")
        for vertex in other._vertices():
            elem = vertex.elem
            path = self._identity_vertex.walk_word(elem)
            assert path is not None
            _edges, projected_vertex = path
            if not (
                len(projected_vertex.forward_edges) == len(vertex.forward_edges)
                and len(projected_vertex.backward_edges) == len(vertex.backward_edges)
            ):
                return False
        return True

    @purestaticmethod
    def intersect_subgroups(
        free_group: FreeGroup, graphs: Sequence["SubgroupOfFreeGroup"]
    ) -> "SubgroupOfFreeGroup":
        # Constructing the product graph by hand.
        res = SubgroupOfFreeGroup._new(free_group)

        mapping_back = {tuple(g._identity_vertex for g in graphs): res._identity_vertex}
        uncleared = set(
            (
                (
                    res._identity_vertex,
                    tuple(g._identity_vertex for g in graphs),
                ),
            )
        )
        while uncleared:
            vertex, images = uncleared.pop()
            for gen in free_group.gens():
                for s in (-1, 1):
                    if vertex.observe_direction(gen, s) is not None:
                        continue
                    individual_directions = tuple(
                        v.observe_direction(gen, s) for v in images
                    )
                    if any(v is None for v in individual_directions):
                        continue

                    individual_images = tuple(
                        (dir[-1] if dir is not None else Vertex(panic()))
                        for dir in individual_directions
                    )

                    if individual_images in mapping_back:
                        new_vertex = mapping_back[individual_images]
                    else:
                        new_vertex = Vertex(vertex.elem * gen**s)
                        mapping_back[individual_images] = new_vertex
                        uncleared.add((new_vertex, individual_images))

                    if s == 1:
                        Edge(vertex, gen, new_vertex)
                    else:
                        Edge(new_vertex, gen, vertex)

        return res

    def with_added_elements(
        self, elements: Sequence[FreeGroupElement]
    ) -> "SubgroupOfFreeGroup":
        res = self.copy()
        for elem in elements:
            res._push_word(elem)
        return res

    @instance_cache
    def is_normal_in(self, other: "SubgroupOfFreeGroup | FreeGroup") -> bool:
        if isinstance(other, FreeGroup):
            other = SubgroupOfFreeGroup._full_subgroup(other)
        if self.free_group != other.free_group:
            raise ValueError("Cannot compare subgroups of different free groups.")
        if not other.contains_subgroup(self):
            raise ValueError("The other subgroup must contain this subgroup.")
        for gen in self.gens():
            for a in other.gens():
                # TODO: figure out when we can get away with not checking inverses.
                # Should work for other = free_group.
                if not self.contains_element(gen.conjugate(a)):
                    return False
                if not self.contains_element(gen.conjugate(~a)):
                    return False
        return True

    @instance_cache
    def normalization_in(
        self, other: "SubgroupOfFreeGroup | FreeGroup"
    ) -> "SubgroupOfFreeGroup":
        # Beware the word problem!

        if isinstance(other, FreeGroup):
            other = SubgroupOfFreeGroup._full_subgroup(other)
        if not other.contains_subgroup(self):
            raise ValueError("Cannot normalize a subgroup not contained in the other.")

        res = self.copy()
        # We must take inverses here.
        gens = other.signed_gens()

        while True:
            normal = True
            for a in res.gens():
                for b in gens:
                    a_conj = a.conjugate(b)
                    if not res.contains_element(a_conj):
                        res._push_word(a_conj)
                        normal = False
            if normal:
                return res

    def normalizer_in(
        self, other: "SubgroupOfFreeGroup | FreeGroup"
    ) -> "SubgroupOfFreeGroup":
        if isinstance(other, FreeGroup):
            other = SubgroupOfFreeGroup._full_subgroup(other)
        if not other.contains_subgroup(self):
            raise ValueError("Cannot normalize a subgroup not contained in the other.")

        gens = list(self.gens())
        for vertex in self._vertices():
            elem = vertex.elem
            if self.conjugate(elem) == self:
                gens.append(elem)
        return SubgroupOfFreeGroup.from_relations(other.free_group, gens)

    def rank(self) -> int:
        return len(self.gens())

    @instance_cache
    def right_coset_representatives_in(
        self, other: "SubgroupOfFreeGroup | FreeGroup"
    ) -> List[FreeGroupElement]:
        if isinstance(other, FreeGroup):
            other = SubgroupOfFreeGroup._full_subgroup(other)
        if self.free_group != other.free_group:
            raise ValueError("Cannot compare subgroups of different free groups.")
        if not other.contains_subgroup(self):
            raise ValueError("The other subgroup must contain this subgroup.")
        if not self.has_finite_index_in(other):
            raise ValueError(
                "The other subgroup must have finite index over this subgroup."
            )

        self._relabel()
        return [v.elem for v in self._vertices() if other.contains_element(v.elem)]

    def left_coset_representatives_in(
        self, other: "SubgroupOfFreeGroup | FreeGroup"
    ) -> List[FreeGroupElement]:
        return [~elem for elem in self.right_coset_representatives_in(other)]

    @instance_cache
    def core_in(
        self, other: "SubgroupOfFreeGroup | FreeGroup"
    ) -> "SubgroupOfFreeGroup":
        if isinstance(other, FreeGroup):
            other = SubgroupOfFreeGroup._full_subgroup(other)
        if self.free_group != other.free_group:
            raise ValueError("Cannot compare subgroups of different free groups.")
        if not other.contains_subgroup(self):
            raise ValueError("The other subgroup must contain this subgroup.")
        if not self.has_finite_index_in(other):
            raise ValueError(
                "The other subgroup must have finite index over this subgroup."
            )
        return SubgroupOfFreeGroup.intersect_subgroups(
            self.free_group,
            [self.conjugate(x) for x in self.left_coset_representatives_in(other)],
        )

    @instance_cache
    def index_in(self, other: "SubgroupOfFreeGroup | FreeGroup") -> int:
        # return len(self._vertices())
        if isinstance(other, FreeGroup):
            other = SubgroupOfFreeGroup._full_subgroup(other)
        if self.free_group != other.free_group:
            raise ValueError("Cannot compare subgroups of different free groups.")
        if not other.contains_subgroup(self):
            raise ValueError("The other subgroup must contain this subgroup.")
        if not self.has_finite_index_in(other):
            raise ValueError(
                "The other subgroup must have finite index over this subgroup."
            )
        return len(self.right_coset_representatives_in(other))

    # When both operands are the same type, python doesn't call __rtruediv__ :)
    def __truediv__(self, other: "SubgroupOfFreeGroup") -> "FiniteGroup":
        return other.__rtruediv__(self)

    def __rtruediv__(self, other: "SubgroupOfFreeGroup | FreeGroup") -> "FiniteGroup":
        from finite_group import FiniteGroup

        if isinstance(other, FreeGroup):
            other = SubgroupOfFreeGroup._full_subgroup(other)
        if self.free_group != other.free_group:
            raise ValueError("Cannot compare subgroups of different free groups.")
        if not other.contains_subgroup(self):
            raise ValueError("The other subgroup must contain this subgroup.")
        if not self.is_normal_in(other):
            raise ValueError("The subgroup must be normal in the other subgroup.")
        if not self.has_finite_index_in(other):
            raise NotImplementedError(
                "Quotients by infinite index normal subgroups are not implemented."
            )
        return FiniteGroup(other, self, code="from SubgroupOfFreeGroup __rdiv__")
