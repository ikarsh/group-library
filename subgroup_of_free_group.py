import itertools
from typing import Dict, List, Literal, Set, Tuple
from free_group import FreeGroup, FreeGroupElement, Letter


class SignedGenerator(FreeGroupElement):
    def __init__(self, free_group: FreeGroup, letter: Letter, sign: Literal[-1, 1]):
        self.letter = letter
        self.sign = sign
        super().__init__(free_group, [(letter, sign)])

    def __invert__(self) -> "SignedGenerator":
        msgn = -self.sign
        assert msgn in (-1, 1)
        return SignedGenerator(self.free_group, self.letter, msgn)


class Vertex:
    def __init__(self, free_group: FreeGroup, elem: FreeGroupElement):
        self.free_group = free_group
        self.elem = elem

    def __repr__(self) -> str:
        return repr(self.elem)


Edge = SignedGenerator


class LabeledEdgeGraph:
    def __init__(self, free_group: FreeGroup):
        self.free_group = free_group
        self.vertices: Set[Vertex] = set()
        self.forward_edges: Dict[Vertex, Set[Tuple[Edge, Vertex]]] = {}

    def add_vertex(self, v: Vertex):
        if self.free_group != v.free_group:
            raise ValueError(f"{v} not in free group {self.free_group}")
        self.vertices.add(v)
        if self.forward_edges.get(v) is None:
            self.forward_edges[v] = set()

    def add_edge(self, v0: Vertex, e: Edge, v1: Vertex):
        if (
            v0.free_group != self.free_group
            or v1.free_group != self.free_group
            or e.free_group != self.free_group
        ):
            raise ValueError(
                f"Edge {v0} --{e}--> {v1} not in free group {self.free_group}"
            )
        if v0 not in self.vertices:
            raise ValueError(f"Vertex {v0} not in graph")
        if v1 not in self.vertices:
            raise ValueError(f"Vertex {v1} not in graph")
        self.forward_edges[v0].add((e, v1))
        self.forward_edges[v1].add((~e, v0))

    def join_vertices(self, v0: Vertex, v1: Vertex) -> None:
        if v0 not in self.vertices:
            raise ValueError(f"Vertex {v0} not in graph")
        if v1 not in self.vertices:
            raise ValueError(f"Vertex {v1} not in graph")
        if v0 == v1:
            raise ValueError("Vertices are the same")
        for e, v in self.forward_edges[v1]:
            if v == v1:
                self.add_edge(v0, e, v0)
            else:
                self.add_edge(v0, e, v)
                self.forward_edges[v].remove((~e, v1))
        self.vertices.remove(v1)
        del self.forward_edges[v1]


class SubgroupOfFreeGroup:
    def __init__(self, free_group: FreeGroup, relations: List[FreeGroupElement]):
        for relation in relations:
            if relation.free_group != free_group:
                raise ValueError(f"Relation {relation} not in free group {free_group}")

        self.free_group = free_group
        self._setup_graph(relations)
        self._reduce_graph()
        self._create_spanning_tree()
        self.free_gens = self._compute_gens_from_graph()

    def gens(self) -> List[FreeGroupElement]:
        return self.free_gens

    def _setup_graph(self, relations: List[FreeGroupElement]):
        self.identity_vertex = Vertex(self.free_group, self.free_group.identity())
        self.labeled_edge_graph = LabeledEdgeGraph(self.free_group)
        self.labeled_edge_graph.add_vertex(self.identity_vertex)
        for relation in relations:
            edge_sequence: List[Edge] = []
            for gen, pow in relation:
                assert pow != 0
                sign = 1 if pow > 0 else -1
                edge = SignedGenerator(self.free_group, gen, sign)
                edge_sequence += [edge] * abs(pow)

            curr_vertex = self.identity_vertex
            for edge in edge_sequence:
                next_vertex = Vertex(self.free_group, curr_vertex.elem * edge)
                self.labeled_edge_graph.add_vertex(next_vertex)
                self.labeled_edge_graph.add_edge(curr_vertex, edge, next_vertex)
                curr_vertex = next_vertex
            assert curr_vertex.elem == relation
            self.labeled_edge_graph.join_vertices(self.identity_vertex, curr_vertex)

    def _reduce_graph(self):
        vertices_to_clean = self.labeled_edge_graph.vertices.copy()
        while vertices_to_clean:
            v = vertices_to_clean.pop()
            for (e1, x1), (e2, x2) in itertools.combinations(
                self.labeled_edge_graph.forward_edges[v], 2
            ):
                if e1 == e2:
                    if (
                        x2.elem.length() <= x1.elem.length()
                    ):  # Pick the shorter word to be the new representative. Later this will be improved.
                        x1, x2 = x2, x1
                    self.labeled_edge_graph.join_vertices(x1, x2)
                    vertices_to_clean.add(x1)
                    vertices_to_clean.add(v)
                    if x2 in vertices_to_clean:
                        vertices_to_clean.remove(x2)
                    break

    def _create_spanning_tree(self):
        # What this function actually does is give every vertex a minimal representative.
        # Minimality is taken with respect to length and then lexicographically.
        # This ensures a spanning tree is created.
        assert self.identity_vertex.elem.is_identity()
        vertices_to_clean = set((self.identity_vertex,))
        while vertices_to_clean:
            v = vertices_to_clean.pop()
            for e, x in self.labeled_edge_graph.forward_edges[v]:
                if v.elem * e < x.elem:
                    x.elem = v.elem * e
                    vertices_to_clean.add(x)

    def _compute_gens_from_graph(self) -> List["FreeGroupElement"]:
        gens: List[FreeGroupElement] = []
        for v0, v0_edges in self.labeled_edge_graph.forward_edges.items():
            for edge, v1 in v0_edges:
                if edge.sign == -1:
                    continue  # No need to do the same edge twice.
                gen = v0.elem * edge * ~v1.elem
                if gen.is_identity():
                    continue
                gens.append(gen)
        return gens
