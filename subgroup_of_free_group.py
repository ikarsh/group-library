from typing import Dict, List, Optional, Set, Tuple
from free_group import (
    FreeGroup,
    FreeGroupElement,
    FreeGroupGenerator,
    FreeGroupTemplate,
    verify,
)


class Vertex(FreeGroupTemplate):
    def __init__(self, elem: FreeGroupElement):
        self.elem = elem
        self.forward_edges: Dict[FreeGroupGenerator, Edge] = {}
        self.backward_edges: Dict[FreeGroupGenerator, Edge] = {}
        super().__init__(elem.free_group)

    def delete(self):
        if self.forward_edges or self.backward_edges:
            raise ValueError("Cannot delete vertex with edges")

    @verify
    def __lt__(self, other: "Vertex") -> bool:
        return self.elem < other.elem

    def __hash__(self) -> int:
        return hash(self.elem)

    def __repr__(self) -> str:
        return repr(self.elem)


class Edge:
    def __init__(self, source: Vertex, elem: FreeGroupGenerator, target: Vertex):
        self.source = source
        self.elem = elem
        self.target = target

        if (
            self.source.forward_edges.get(self.elem) is not None
            or self.target.backward_edges.get(self.elem) is not None
        ):
            raise ValueError(f"This shouldn't happen.")
        self.source.forward_edges[self.elem] = self
        self.target.backward_edges[self.elem] = self

    def delete(self):
        if (self.source.forward_edges.get(self.elem) is not self) or (
            self.target.backward_edges.get(self.elem) is not self
        ):
            raise ValueError(f"This shouldn't happen")
        del self.source.forward_edges[self.elem]
        del self.target.backward_edges[self.elem]

    def __hash__(self) -> int:
        return hash((self.source, self.elem, self.target))

    def __lt__(self, other: "Edge") -> bool:
        return (self.source, self.elem, self.target) < (
            other.source,
            other.elem,
            other.target,
        )

    def __repr__(self) -> str:
        return f"{self.source} -- {self.elem} --> {self.target}"


class _SubgroupGraph:
    def __init__(self, free_group: FreeGroup):
        self.free_group = free_group
        self.identity_vertex = Vertex(free_group.identity())
        self.vertices: Set[Vertex] = set((self.identity_vertex,))
        self.edges: Set[Edge] = set()

    def add_vertex(self, elem: FreeGroupElement) -> Vertex:
        new_vertex = Vertex(elem)
        self.vertices.add(new_vertex)
        return new_vertex

    def remove_vertex(self, vertex: Vertex):
        self.vertices.remove(vertex)
        vertex.delete()

    def add_edge(self, source: Vertex, elem: FreeGroupGenerator, target: Vertex):
        self.edges.add(Edge(source, elem, target))

    def remove_edge(self, edge: Edge):
        self.edges.remove(edge)
        edge.delete()

    def add_word(self, word: FreeGroupElement):
        vertex = self.identity_vertex
        for gen, pow in word:
            sign = 1 if pow > 0 else -1
            for _ in range(abs(pow)):
                if sign == 1:
                    if vertex.forward_edges.get(gen) is not None:
                        vertex = vertex.forward_edges[gen].target
                    else:
                        new_vertex = self.add_vertex(vertex.elem * gen)
                        self.add_edge(vertex, gen, new_vertex)
                        vertex = new_vertex
                else:
                    if vertex.backward_edges.get(gen) is not None:
                        vertex = vertex.backward_edges[gen].source
                    else:
                        new_vertex = self.add_vertex(vertex.elem * ~gen)
                        self.add_edge(new_vertex, gen, vertex)
                        vertex = new_vertex

        self.glue(vertex, self.identity_vertex)

    def glue(self, v0: Vertex, v1: Vertex):
        # Replaces v0 by v1, recursively.
        glues = set(((v0, v1),))

        while glues:
            v0, v1 = glues.pop()
            if v0 == v1:
                continue

            assert v0 in self.vertices and v1 in self.vertices
            if v0.elem < v1.elem:
                v0, v1 = v1, v0

            for gen, edge in sorted(v0.forward_edges.items()):
                assert edge.elem == gen
                self.remove_edge(edge)
                v1_next = v1.forward_edges.get(gen)

                # Annoying edgecase
                if edge.target == v0:
                    v1_prev = v1.backward_edges.get(gen)
                    if v1_next is not None:
                        glues.add((v1, v1_next.target))
                    if v1_prev is not None:
                        glues.add((v1_prev.source, v1))
                    if v1_prev is None and v1_next is None:
                        self.add_edge(v1, gen, v1)
                else:
                    if v1_next is None:
                        self.add_edge(v1, gen, edge.target)
                    else:
                        glues.add((edge.target, v1_next.target))

            for gen, edge in sorted(v0.backward_edges.items()):
                self.remove_edge(edge)
                v1_prev = v1.backward_edges.get(gen)
                # The edgecase does not happen here.

                if v1_prev is None:
                    self.add_edge(edge.source, gen, v1)
                else:
                    glues.add((edge.source, v1_prev.source))

            self.remove_vertex(v0)
            for pair in list(glues):
                if pair[0] == pair[1]:
                    glues.remove(pair)
                elif v0 in pair:
                    glues.remove(pair)
                    other = pair[1 - pair.index(v0)]
                    glues.add((other, v1))

    def relabel(self):
        # What this function actually does is give every vertex a minimal representative.
        # Minimality is taken with respect to length and then lexicographically.
        # This ensures a spanning tree is created.
        vertices_to_clean = self.vertices.copy()
        while vertices_to_clean:
            v = vertices_to_clean.pop()
            for edge in sorted(v.forward_edges.values()):
                if edge.source.elem * edge.elem < edge.target.elem:
                    edge.target.elem = edge.source.elem * edge.elem
                    vertices_to_clean.add(edge.target)
            for edge in sorted(v.backward_edges.values()):
                if edge.target.elem * ~edge.elem < edge.source.elem:
                    edge.source.elem = edge.target.elem * ~edge.elem
                    vertices_to_clean.add(edge.source)

    def special_edges(self) -> List[Edge]:
        return [
            edge
            for edge in sorted(self.edges)
            if edge.source.elem * edge.elem != edge.target.elem
        ]


class SubgroupOfFreeGroup(FreeGroupTemplate):
    def __init__(self, free_group: FreeGroup, relations: List[FreeGroupElement]):
        for relation in relations:
            if relation.free_group != free_group:
                raise ValueError(f"Relation {relation} not in free group {free_group}")

        self._graph = _SubgroupGraph(free_group)
        for relation in relations:
            self._graph.add_word(relation)
        self._graph.relabel()

        # We list the edges outside the spanning tree. They correspond to the free generators.
        self._special_edges = self._graph.special_edges()
        self._gens_from_edges = {
            edge: edge.source.elem * edge.elem * ~edge.target.elem
            for edge in self._special_edges
        }

        super().__init__(free_group)

    def __repr__(self) -> str:
        return f"Subgroup of {self.free_group} with free basis {self.gens()}"

    def gens(self) -> List[FreeGroupElement]:
        return list(self._gens_from_edges.values())

    def coset_representatives(self) -> List[FreeGroupElement]:
        return [v.elem for v in sorted(self._graph.vertices)]

    @verify
    def express(
        self, elem: FreeGroupElement
    ) -> Optional[List[Tuple[FreeGroupElement, int]]]:
        vertex = self._graph.identity_vertex
        result: List[Tuple[FreeGroupElement, int]] = []
        for gen, pow in elem:
            sign = 1 if pow > 0 else -1
            if sign == 1:
                for _ in range(pow):
                    edge = vertex.forward_edges.get(gen)
                    if edge is None:
                        return None
                    if edge in self._special_edges:
                        new_gen = self._gens_from_edges[edge]
                        if result and result[-1][0] == new_gen:
                            result[-1] = (new_gen, result[-1][1] + 1)
                        else:
                            result.append((self._gens_from_edges[edge], 1))
                    vertex = edge.target
            else:
                for _ in range(-pow):
                    edge = vertex.backward_edges.get(gen)
                    if edge is None:
                        return None
                    if edge in self._special_edges:
                        new_gen = self._gens_from_edges[edge]
                        if result and result[-1][0] == new_gen:
                            result[-1] = (new_gen, result[-1][1] - 1)
                        else:
                            result.append((self._gens_from_edges[edge], -1))
                    vertex = edge.source
                if result and result[-1][1] == 0:
                    result.pop()

        if vertex != self._graph.identity_vertex:
            return None
        return result

    @verify
    def contains_element(self, elem: FreeGroupElement) -> bool:
        return self.express(elem) is not None

    @verify
    def contains_subgroup(self, other: "SubgroupOfFreeGroup") -> bool:
        for gen in other.gens():
            if not self.contains_element(gen):
                return False
        return True

    @verify
    def equals_subgroup(self, other: "SubgroupOfFreeGroup") -> bool:
        return self.contains_subgroup(other) and other.contains_subgroup(self)

    @verify
    def conjugate(self, elem: FreeGroupElement) -> "SubgroupOfFreeGroup":
        return SubgroupOfFreeGroup(
            self.free_group,
            [gen.conjugate(elem) for gen in self.gens()],
        )

    def is_normal(self) -> bool:
        # TODO improve, this is a very naive implementation
        for gen in self.free_group.gens():
            if not self.conjugate(gen).equals_subgroup(self):
                return False
        return True

    def _one_normalization_step(self) -> "SubgroupOfFreeGroup":
        return self.free_group.subgroup(
            [gen.conjugate(a) for gen in self.gens() for a in self.free_group.gens()]
        )

    def normalization(self) -> "SubgroupOfFreeGroup":
        # This may run forever. Beware!!!
        next_step = self._one_normalization_step()

        if self.equals_subgroup(next_step):
            return self

        return next_step.normalization()

    def index(self) -> int:
        assert self.is_normal()
        return len(self._graph.vertices)

    def rank(self) -> int:
        return len(self.gens())
