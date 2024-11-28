from typing import Dict, List, Optional, Set, Tuple
from free_group import (
    FreeGroup,
    FreeGroupElement,
    FreeGroupGenerator,
    FreeGroupTemplate,
)


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
        if (self.source.forward_edges.get(self.elem) is not self) or (
            self.target.backward_edges.get(self.elem) is not self
        ):
            raise ValueError(f"This shouldn't happen")
        del self.source.forward_edges[self.elem]
        del self.target.backward_edges[self.elem]

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


class _SubgroupGraph:
    def __init__(self, free_group: FreeGroup):
        self.free_group = free_group
        self._identity_vertex = Vertex(free_group.identity())
        self._vertices: Set[Vertex] = set((self._identity_vertex,))
        self._edges: Set[Edge] = set()

        self.reset_cache()

    def reset_cache(self):
        self._cycle_generators: Optional[Dict[Edge, FreeGroupElement]] = None
        self._coset_representatives: Optional[List[FreeGroupElement]] = None

    def add_vertex(self, elem: FreeGroupElement) -> Vertex:
        new_vertex = Vertex(elem)
        self._vertices.add(new_vertex)
        return new_vertex

    def remove_vertex(self, vertex: Vertex):
        self._vertices.remove(vertex)
        vertex.delete()

    def add_edge(self, source: Vertex, elem: FreeGroupGenerator, target: Vertex):
        self._edges.add(Edge(source, elem, target))

    def remove_edge(self, edge: Edge):
        self._edges.remove(edge)
        edge.delete()

    def push_word(self, word: FreeGroupElement):
        self.reset_cache()
        vertex = self._identity_vertex
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

        self.glue(vertex, self._identity_vertex)

    def glue(self, v0: Vertex, v1: Vertex):
        # Replaces v0 by v1, recursively.
        glues = [(v0, v1)]

        while glues:
            v0, v1 = glues.pop()
            if v0 == v1:
                continue

            assert v0 in self._vertices and v1 in self._vertices
            if v0.elem < v1.elem:
                v0, v1 = v1, v0

            for gen, edge in list(v0.forward_edges.items()):
                assert edge.elem == gen
                self.remove_edge(edge)
                v1_next = v1.forward_edges.get(gen)

                # Annoying edgecase
                if edge.target == v0:
                    v1_prev = v1.backward_edges.get(gen)
                    if v1_next is not None:
                        glues.append((v1, v1_next.target))
                    if v1_prev is not None:
                        glues.append((v1_prev.source, v1))
                    if v1_prev is None and v1_next is None:
                        self.add_edge(v1, gen, v1)
                else:
                    if v1_next is None:
                        self.add_edge(v1, gen, edge.target)
                    else:
                        glues.append((edge.target, v1_next.target))

            for gen, edge in list(v0.backward_edges.items()):
                self.remove_edge(edge)
                v1_prev = v1.backward_edges.get(gen)
                # The edgecase does not happen here.

                if v1_prev is None:
                    self.add_edge(edge.source, gen, v1)
                else:
                    glues.append((edge.source, v1_prev.source))

            self.remove_vertex(v0)
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
        uncleared_vertices = set(self._vertices)

        while uncleared_vertices:
            v = uncleared_vertices.pop()
            for edge in v.forward_edges.values():
                if edge.source.elem * edge.elem < edge.target.elem:
                    edge.target.elem = edge.source.elem * edge.elem
                    uncleared_vertices.add(edge.target)
            for edge in v.backward_edges.values():
                if edge.target.elem * ~edge.elem < edge.source.elem:
                    edge.source.elem = edge.target.elem * ~edge.elem
                    uncleared_vertices.add(edge.source)

        # assert (
        #     len(self._edges) == len(self.cycle_generators()) + len(self._vertices) - 1
        # )

    def cycle_generators(self) -> Dict[Edge, FreeGroupElement]:
        if self._cycle_generators is None:
            self._relabel()
            self._cycle_generators = {
                edge: value
                for edge in self._edges
                if not (
                    value := edge.source.elem * edge.elem * ~edge.target.elem
                ).is_identity()
            }
        return self._cycle_generators

    def coset_representatives(self) -> List[FreeGroupElement]:
        if self._coset_representatives is None:
            self._relabel()
            self._coset_representatives = [v.elem for v in self._vertices]
        return self._coset_representatives

    def express(
        self, elem: FreeGroupElement
    ) -> Optional[List[Tuple[FreeGroupElement, int]]]:
        vertex = self._identity_vertex
        result: List[Tuple[FreeGroupElement, int]] = []
        for gen, pow in elem:
            sign = 1 if pow > 0 else -1
            if sign == 1:
                for _ in range(pow):
                    edge = vertex.forward_edges.get(gen)
                    if edge is None:
                        return None
                    new_gen = self.cycle_generators().get(edge)
                    if new_gen is not None:
                        if result and result[-1][0] == new_gen:
                            result[-1] = (new_gen, result[-1][1] + 1)
                        else:
                            result.append((new_gen, 1))
                    vertex = edge.target
            else:
                for _ in range(-pow):
                    edge = vertex.backward_edges.get(gen)
                    if edge is None:
                        return None
                    new_gen = self.cycle_generators().get(edge)
                    if new_gen is not None:
                        if result and result[-1][0] == new_gen:
                            result[-1] = (new_gen, result[-1][1] - 1)
                        else:
                            result.append((new_gen, -1))
                    vertex = edge.source
                if result and result[-1][1] == 0:
                    result.pop()

        if vertex != self._identity_vertex:
            return None
        return result

    def index(self) -> int:
        return len(self._vertices)


class SubgroupOfFreeGroup(FreeGroupTemplate):
    def __init__(self, free_group: FreeGroup):
        self._graph = _SubgroupGraph(free_group)
        self.reset_cache()
        super().__init__(free_group)

    def reset_cache(self):
        # These are the edges outside of the spanning tree. They correspond to the generators.
        self._special_edges: Optional[List[Edge]] = None

        # This is the correspondence.
        self._gens_from_edges: Optional[Dict[Edge, FreeGroupElement]] = None

    @classmethod
    def from_relations(
        cls, free_group: FreeGroup, relations: List[FreeGroupElement]
    ) -> "SubgroupOfFreeGroup":
        for relation in relations:
            if relation.free_group != free_group:
                raise ValueError(f"Relation {relation} not in free group {free_group}")

        res = SubgroupOfFreeGroup(free_group)
        for relation in relations:
            res.push_word(relation)
        return res

    def push_word(self, word: FreeGroupElement):
        self._graph.push_word(word)
        self.reset_cache()

    def __repr__(self) -> str:
        return f"Subgroup of {self.free_group} with free basis {self.gens()}"

    def gens(self) -> List[FreeGroupElement]:
        return list(self._graph.cycle_generators().values())

    def coset_representatives(self) -> List[FreeGroupElement]:
        return self._graph.coset_representatives()

    def express(
        self, elem: FreeGroupElement
    ) -> Optional[List[Tuple[FreeGroupElement, int]]]:
        return self._graph.express(elem)

    def contains_element(self, elem: FreeGroupElement) -> bool:
        return self.express(elem) is not None

    def contains_subgroup(self, other: "SubgroupOfFreeGroup") -> bool:
        for gen in other.gens():
            if not self.contains_element(gen):
                return False
        return True

    def equals_subgroup(self, other: "SubgroupOfFreeGroup") -> bool:
        return self.contains_subgroup(other) and other.contains_subgroup(self)

    def conjugate(self, elem: FreeGroupElement) -> "SubgroupOfFreeGroup":
        return SubgroupOfFreeGroup.from_relations(
            self.free_group,
            [gen.conjugate(elem) for gen in self.gens()],
        )

    def is_normal(self) -> bool:
        # TODO this is faster code that works in the case of finite index. Maybe it can be generalized?
        # for v in self._graph.vertices:
        #     if not (
        #         len(v.forward_edges) == len(v.backward_edges) == self.free_group.rank()
        #     ):
        #         return False
        # for edge in self._graph.edges:
        #     for gen in self.free_group.gens():
        #         new_source = edge.source.forward_edges[gen].target
        #         new_target = edge.target.forward_edges[gen].target
        #         new_edge = new_source.forward_edges.get(gen)
        #         assert new_edge is not None
        #         if new_edge.target != new_target:
        #             return False
        # return True

        for gen in self.gens():
            for a in self.free_group.gens():
                if not self.contains_element(gen.conjugate(a)):
                    return False
        return True

    def _one_normalization_step(self) -> "SubgroupOfFreeGroup":
        return self.free_group.subgroup(
            self.gens()
            + [
                gen.conjugate(a**s)
                for gen in self.gens()
                for a in self.free_group.gens()
                for s in (-1, 1)
            ]
        )

    def normalization(self, depth: int = 20) -> "SubgroupOfFreeGroup":
        # Beware the word problem!

        current = self

        for _ in range(depth + 1):
            next_step = current._one_normalization_step()
            if current.equals_subgroup(next_step):
                return current
            current = next_step

        raise RuntimeError(f"Normalization did not converge in {depth} steps")

    def index(self) -> int:
        assert self.is_normal()
        return self._graph.index()

    def rank(self) -> int:
        return len(self.gens())
