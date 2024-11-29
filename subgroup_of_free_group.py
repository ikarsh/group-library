from typing import Dict, List, Optional, Set, Tuple
from free_group import (
    FreeGroup,
    FreeGroupElement,
    FreeGroupGenerator,
)
from word import Word


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

    def walk_edge(self, gen: FreeGroupGenerator, sign: int) -> Optional["Vertex"]:
        dir = self.observe_direction(gen, sign)
        return None if dir is None else dir[1]

    def walk_edge_violent(self, gen: FreeGroupGenerator, sign: int) -> "Vertex":
        # If this can't find a way, it will create one.
        v = self.walk_edge(gen, sign)
        if v is not None:
            return v
        if sign == 1:
            new_vertex = Vertex(self.elem * gen)
            Edge(self, gen, new_vertex)
            return new_vertex
        else:
            new_vertex = Vertex(self.elem * ~gen)
            Edge(new_vertex, gen, self)
            return new_vertex

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

        self.reset_cache()

    def copy(self) -> "_SubgroupGraph":
        new_graph = _SubgroupGraph(self.free_group)
        vertex_mapping = {self._identity_vertex: new_graph._identity_vertex}
        for vertex in self.vertices():
            if vertex != self._identity_vertex:
                vertex_mapping[vertex] = Vertex(vertex.elem)
        for edge in self.edges():
            Edge(vertex_mapping[edge.source], edge.elem, vertex_mapping[edge.target])
        return new_graph

    def conjugate(self, elem: FreeGroupElement) -> "_SubgroupGraph":
        new_graph = self.copy()
        vertex = self._identity_vertex
        for gen, pow in ~elem:
            vertex = vertex.walk_edge_violent(gen, pow)
        new_graph._identity_vertex = vertex
        return new_graph

    def reset_cache(self):
        self._cycle_generators: Optional[Dict[Edge, FreeGroupElement]] = None
        self._coset_representatives: Optional[List[FreeGroupElement]] = None
        self._vertices: Optional[Set[Vertex]] = None
        self._edges: Optional[Set[Edge]] = None

    def vertices(self) -> Set[Vertex]:
        if self._vertices is None:
            self._vertices = set((self._identity_vertex,))
            unchecked = set((self._identity_vertex,))
            while unchecked:
                vertex = unchecked.pop()
                for edge in vertex.forward_edges.values():
                    if not edge.target in self._vertices:
                        unchecked.add(edge.target)
                        self._vertices.add(edge.target)
                for edge in vertex.backward_edges.values():
                    if not edge.source in self._vertices:
                        unchecked.add(edge.source)
                        self._vertices.add(edge.source)
        return self._vertices.copy()

    def edges(self) -> Set[Edge]:
        if self._edges is None:
            self._edges = set()
            for vertex in self.vertices():
                for edge in vertex.forward_edges.values():
                    self._edges.add(edge)
                for edge in vertex.backward_edges.values():
                    self._edges.add(edge)
        return self._edges.copy()

    def push_word(self, word: FreeGroupElement):
        self.reset_cache()
        vertex = self._identity_vertex
        for gen, pow in word:
            sign = 1 if pow > 0 else -1
            for _ in range(abs(pow)):
                vertex = vertex.walk_edge_violent(gen, sign)

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
        uncleared_vertices = self.vertices().copy()

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

        # assert (
        #     len(self._edges) == len(self.cycle_generators()) + len(self._vertices) - 1
        # )

    def cycle_generators(self) -> Dict[Edge, FreeGroupElement]:
        if self._cycle_generators is None:
            self._relabel()
            self._cycle_generators = {
                edge: value
                for edge in self.edges()
                if not (
                    value := edge.source.elem * edge.elem * ~edge.target.elem
                ).is_identity()
            }
        return self._cycle_generators

    def coset_representatives(self) -> List[FreeGroupElement]:
        if self._coset_representatives is None:
            self._relabel()
            self._coset_representatives = [v.elem for v in self.vertices()]
        return self._coset_representatives

    def express(self, elem: FreeGroupElement) -> Optional[Word[FreeGroupElement]]:
        vertex = self._identity_vertex
        result: Word[FreeGroupElement] = Word().identity()
        for gen, pow in elem:
            sign = 1 if pow > 0 else -1

            for _ in range(abs(pow)):
                dir = vertex.observe_direction(gen, sign)
                if dir is None:
                    return None
                edge, vertex = dir

                new_gen = self.cycle_generators().get(edge)
                if new_gen is not None:
                    result.add(new_gen, sign)

        if vertex != self._identity_vertex:
            return None
        return result

    def contains_element(self, elem: FreeGroupElement) -> bool:
        vertex = self._identity_vertex
        for gen, pow in elem:
            sign = 1 if pow > 0 else -1
            for _ in range(abs(pow)):
                vertex = vertex.walk_edge(gen, sign)
                if vertex is None:
                    return False
        return vertex == self._identity_vertex

    def index(self) -> int:
        return len(self.vertices())


class SubgroupOfFreeGroup:
    def __init__(self, free_group: FreeGroup):
        self._graph = _SubgroupGraph(free_group)
        self.free_group = free_group

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

    @classmethod
    def _from_graph(cls, graph: _SubgroupGraph) -> "SubgroupOfFreeGroup":
        # Use carefully! This does not verify input.
        res = SubgroupOfFreeGroup(graph.free_group)
        res._graph = graph
        return res

    def __repr__(self) -> str:
        return f"Subgroup of {self.free_group} with free basis {self.gens()}"

    def gens(self) -> List[FreeGroupElement]:
        return list(self._graph.cycle_generators().values())

    def coset_representatives(self) -> List[FreeGroupElement]:
        return self._graph.coset_representatives()

    def express(self, elem: FreeGroupElement) -> Optional[Word[FreeGroupElement]]:
        return self._graph.express(elem)

    def contains_element(self, elem: FreeGroupElement) -> bool:
        return self._graph.contains_element(elem)

    def contains_subgroup(self, other: "SubgroupOfFreeGroup") -> bool:
        for gen in other.gens():
            if not self.contains_element(gen):
                return False
        return True

    def equals_subgroup(self, other: "SubgroupOfFreeGroup") -> bool:
        return self.contains_subgroup(other) and other.contains_subgroup(self)

    def conjugate(self, elem: FreeGroupElement) -> "SubgroupOfFreeGroup":
        new_graph = self._graph.conjugate(elem)
        return SubgroupOfFreeGroup._from_graph(new_graph)

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
