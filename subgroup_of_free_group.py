import itertools
from typing import Dict, List, Literal, Optional, Set, Tuple
from free_group import FreeGroup, FreeGroupElement, FreeGroupGenerator


Vertex = FreeGroupElement
Edge = Tuple[FreeGroupGenerator, Literal[-1, 1]]


def flip(x: Edge) -> Edge:
    a, n = x
    return a, -n


def value(x: Edge) -> "FreeGroupElement":
    a, n = x
    if n == 1:
        return a.as_group_element()
    elif n == -1:
        return ~a
    assert False


class LabeledEdgeGraph:
    def __init__(self, free_group: FreeGroup):
        self.free_group = free_group
        self.vertices: Set[Vertex] = set()
        self.forward_edges: Dict[Vertex, Set[Tuple[Vertex, Edge]]] = {}

    def add_vertex(self, v: Vertex):
        if v.free_group != self.free_group:
            raise ValueError(f"Vertex {v} not in free group {self.free_group}")
        self.vertices.add(v)
        if self.forward_edges.get(v) is None:
            self.forward_edges[v] = set()

    def add_edge(self, v0: Vertex, v1: Vertex, e: Edge):
        if (
            v0.free_group != self.free_group
            or v1.free_group != self.free_group
            or e[0].free_group != self.free_group
        ):
            raise ValueError(
                f"Edge {v0} --{e}--> {v1} not in free group {self.free_group}"
            )
        if v0 not in self.vertices:
            raise ValueError(f"Vertex {v0} not in graph")
        if v1 not in self.vertices:
            raise ValueError(f"Vertex {v1} not in graph")
        self.forward_edges[v0].add((v1, e))
        self.forward_edges[v1].add((v0, flip(e)))

    def join_vertices(self, v0: Vertex, v1: Vertex) -> None:
        if v0 not in self.vertices:
            raise ValueError(f"Vertex {v0} not in graph")
        if v1 not in self.vertices:
            raise ValueError(f"Vertex {v1} not in graph")
        if v0 == v1:
            raise ValueError("Vertices are the same")
        for v, e in self.forward_edges[v1]:
            self.add_edge(v0, v, e)
            self.forward_edges[v].remove((v1, flip(e)))
        self.vertices.remove(v1)
        del self.forward_edges[v1]


class SubgroupOfFreeGroup:
    def __init__(self, free_group: FreeGroup, relations: List[FreeGroupElement]):
        for relation in relations:
            if relation.free_group != free_group:
                raise ValueError(f"Relation {relation} not in free group {free_group}")

        self.free_group = free_group
        self.setup_graph(relations)
        self.free_gens = self.gens_from_graph()

    def setup_graph(self, relations: List[FreeGroupElement]):
        self.labeled_edge_graph = LabeledEdgeGraph(self.free_group)
        self.labeled_edge_graph.add_vertex(self.free_group.identity())
        for relation in relations:
            relation_sequence: List[Edge] = []
            for gen, pow in relation.reduce():
                assert pow != 0
                sign = 1 if pow > 0 else -1
                for _ in range(abs(pow)):
                    relation_sequence.append((gen, sign))

            curr_elem = self.free_group.identity()
            for sgen in relation_sequence:
                next_elem = curr_elem * value(sgen)
                self.labeled_edge_graph.add_vertex(next_elem)
                self.labeled_edge_graph.add_edge(curr_elem, next_elem, sgen)
                curr_elem = next_elem
            assert curr_elem == relation
            self.labeled_edge_graph.join_vertices(self.free_group.identity(), curr_elem)

        vertices_to_clean = self.labeled_edge_graph.vertices.copy()
        while vertices_to_clean:
            v = vertices_to_clean.pop()
            for (x1, e1), (x2, e2) in itertools.combinations(
                self.labeled_edge_graph.forward_edges[v], 2
            ):
                if e1 == e2:
                    self.labeled_edge_graph.join_vertices(x1, x2)
                    vertices_to_clean.add(x1)
                    vertices_to_clean.add(v)
                    break

    def gens_from_graph(self) -> List["FreeGroupElement"]:
        def cycles_from(
            curr_word: "FreeGroupElement",
            vertex_sequence: List[Vertex],
            last_edge: Optional[Edge],
        ) -> List["FreeGroupElement"]:
            cycles: List[FreeGroupElement] = []
            curr_vertex = vertex_sequence[-1]
            for next_vertex, edge in self.labeled_edge_graph.forward_edges[curr_vertex]:
                if last_edge and edge == flip(last_edge):
                    continue
                new_word = curr_word * value(edge)
                if next_vertex in vertex_sequence:
                    if next_vertex == vertex_sequence[0]:
                        cycles.append(new_word)

                    continue
                cycles += cycles_from(new_word, vertex_sequence + [next_vertex], edge)
            return cycles

        cycles = cycles_from(
            self.free_group.identity(), [self.free_group.identity()], None
        )
        # This is almost what we need. Just need to remove invertions.

        gens: List[FreeGroupElement] = []
        for cycle in cycles:
            if cycle in gens or ~cycle in gens:
                continue
            gens.append(cycle)
        return gens
