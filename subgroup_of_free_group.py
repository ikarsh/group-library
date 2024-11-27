from typing import Dict, List, Set
from free_group import FreeGroup, FreeGroupElement, FreeGroupGenerator


class Vertex:
    def __init__(self, elem: FreeGroupElement):
        self.free_group = elem.free_group
        self.elem = elem
        self.forward_edges: Dict[FreeGroupGenerator, Edge] = {}
        self.backward_edges: Dict[FreeGroupGenerator, Edge] = {}

    def delete(self):
        if self.forward_edges or self.backward_edges:
            raise ValueError("Cannot delete vertex with edges")

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

    def __repr__(self) -> str:
        return f"{self.source} -- {self.elem} --> {self.target}"


class _SubgroupGraph:
    def __init__(self, free_group: FreeGroup):
        self.free_group = free_group
        self.identity_vertex = Vertex(free_group.identity())
        self.edges: Set[Edge] = set()

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
                        new_vertex = Vertex(vertex.elem * gen)
                        self.add_edge(vertex, gen, new_vertex)
                        vertex = new_vertex
                else:
                    if vertex.backward_edges.get(gen) is not None:
                        vertex = vertex.backward_edges[gen].source
                    else:
                        new_vertex = Vertex(vertex.elem * ~gen)
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

            for gen, edge in list(v0.forward_edges.items()):
                self.remove_edge(edge)
                v1_next = v1.forward_edges.get(gen)

                # Annoying edgecase
                if edge.target == v0:
                    if v1_next is None:
                        self.add_edge(v1, gen, v1)
                else:
                    if v1_next is None:
                        self.add_edge(v1, gen, edge.target)
                    else:
                        glues.add((edge.target, v1_next.target))

            for gen, edge in list(v0.backward_edges.items()):
                self.remove_edge(edge)
                v1_prev = v1.backward_edges.get(gen)
                # The edgecase does not happen here.

                if v1_prev is None:
                    self.add_edge(edge.source, gen, v1)
                else:
                    glues.add((edge.source, v1_prev.source))

            v0.delete()

    def relabel(self):
        # What this function actually does is give every vertex a minimal representative.
        # Minimality is taken with respect to length and then lexicographically.
        # This ensures a spanning tree is created.
        vertices_to_clean = set((self.identity_vertex,))
        while vertices_to_clean:
            v = vertices_to_clean.pop()
            for edge in v.forward_edges.values():
                if edge.source.elem * edge.elem < edge.target.elem:
                    edge.target.elem = edge.source.elem * edge.elem
                    vertices_to_clean.add(edge.target)
            for edge in v.backward_edges.values():
                if edge.target.elem * ~edge.elem < edge.source.elem:
                    edge.source.elem = edge.target.elem * ~edge.elem
                    vertices_to_clean.add(edge.source)

    def special_edges(self) -> List[Edge]:
        return [
            edge
            for edge in self.edges
            if edge.source.elem * edge.elem != edge.target.elem
        ]


class SubgroupOfFreeGroup:
    def __init__(self, free_group: FreeGroup, relations: List[FreeGroupElement]):
        for relation in relations:
            if relation.free_group != free_group:
                raise ValueError(f"Relation {relation} not in free group {free_group}")

        self.free_group = free_group
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

    def gens(self) -> List[FreeGroupElement]:
        return list(self._gens_from_edges.values())

    # def express(
    #     self, elem: FreeGroupElement
    # ) -> Optional[List[Tuple[FreeGroupElement, int]]]:
    #     if elem.free_group != self.free_group:
    #         raise ValueError(f"Element {elem} not in free group {self.free_group}")
    #     res: List[Tuple[FreeGroupElement, int]] = []
    #     vertex = self._identity_vertex
    #     for let, pow in elem:
    #         for edge, next_vertex in self._subgroup_graph.forward_edges[vertex]:
    #             if edge.letter == let and edge.sign == sign(pow):

    #                 res.append((edge, pow))
    #                 vertex = next_vertex
    #                 break
    #         else

    # return res
