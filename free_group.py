

import itertools
from typing import Generic, List, Set, Tuple, TypeVar

class FreeGroup:
    def __init__(self, gen_names: Tuple[str], name=None):
        for gen in gen_names:
            if not (gen and gen[0].isalpha() and gen.isalnum()):
                raise ValueError(f"Invalid generator: {gen}")
        for (gen0, gen1) in itertools.combinations(gen_names, 2):
            if gen0.startswith(gen1) or gen1.startswith(gen0):
                raise ValueError(f"Generators cannot be prefixes of each other: {gen0}, {gen1}")
        self.gen_names = gen_names
        self.name = name

    def __repr__(self):
        return f"FreeGroup({self.gen_names})" if self.name is None else self.name
    
    def identity(self):
        return FreeGroupElement(self, [])

    def gens(self):
        return [FreeGroupElement(self, [(gen, 1)]) for gen in self.gen_names]

class FreeGroupElement:
    def __init__(self, free_group: FreeGroup, word: List[Tuple[str, int]]):
        for (gen, power) in word:
            if gen not in free_group.gen_names:
                raise ValueError(f"Generator {gen} not in free group {free_group}")

        self.free_group = free_group
        self.word = word

    def __repr__(self):
        return "".join([gen + "^" + str(power) if power != 1 else gen for (gen, power) in self.word])
    
    def from_str(self, s_: str) -> "FreeGroupElement":
        word = []
        s = s_.replace(" ", "")
        while s:
            for gen in self.group.gens:
                if s.startswith(gen):
                    s = s[len(gen):]
                    if s.startswith("^"):
                        s = s[1:]
                        power = 0
                        sign = 1
                        if s.startswith("-"):
                            s = s[1:]
                            sign = -1
                        while s and s[0].isdigit():
                            power = 10 * power + int(s[0])
                            s = s[1:]
                        else:
                            raise ValueError(f"Invalid power in {s_}")
                        power *= sign
                    else:
                        power = 1

                    word.append((gen, power))
                    break
            else:
                raise ValueError(f"Invalid generator in {s_}")

        return FreeGroupElement(self.free_group, word).reduce()
    
    def reduce(self) -> "FreeGroupElement":
        word = []
        for (gen, power) in self.word:
            if word and word[-1][0] == gen:
                word[-1] = (gen, word[-1][1] + power)
            else:
                word.append((gen, power))
            if word and word[-1][1] == 0:
                word.pop()
        return FreeGroupElement(self.free_group, word)
    
    def __mul__(self, other: "FreeGroupElement") -> "FreeGroupElement":
        if self.free_group != other.free_group:
            raise ValueError(f"Cannot multiply elements from different free groups: {self.free_group}, {other.free_group}")
        word = self.word.copy()
        # Reduction
        for (gen, power) in other.word:
            if word and word[-1][0] == gen:
                word[-1] = (gen, word[-1][1] + power)
                if word[-1][1] == 0:
                    word.pop()
            else:
                word.append((gen, power))
        return FreeGroupElement(self.free_group, word)
    
    def __invert__(self) -> "FreeGroupElement":
        return FreeGroupElement(self.free_group, [(gen, -power) for (gen, power) in self.word[::-1]])
    
    def __pow__(self, n: int) -> "FreeGroupElement":
        if n == 0:
            return self.free_group.identity()
        elif n < 0:
            return ~self ** -n
        else:
            half = n // 2
            half_power = self ** half
            if n % 2 == 0:
                return half_power * half_power
            else:
                return half_power * half_power * self
    
    def conjugate(self, other: "FreeGroupElement") -> "FreeGroupElement":
        return other * self * ~other

# class EdgeLabel:
#     def __init(self, label: str):
#         self.label = label
#         self.aligned = True
    
#     def toggle(self):
#         self.aligned = not self.aligned
    
#     def __eq__(self, edge_label: "EdgeLabel"):
#         return self.label == edge_label.label and self.aligned == edge_label.aligned

# class LabeledEdgeGraph:
#     def __init__(self):
#         self.vertices = set()
#         self.edges = set()
#         self.forward_edges = {}
#         self.backward_edges = {}
    
#     def add_vertex(self, v: str):
#         if v in self.vertices:
#             return # v already in graph
#         self.vertices.add(v)
#         self.forward_edges[v] = set()
#         self.backward_edges[v] = set()
    
#     def add_edge(self, v0: str, v1: str, label: str):
#         if v0 not in self.vertices:
#             raise ValueError(f"Vertex {v0} not in graph")
#         if v1 not in self.vertices:
#             raise ValueError(f"Vertex {v1} not in graph")
#         if (v0, v1, label) in self.edges:
#             return
#         self.edges.add((v0, v1, label))
#         self.forward_edges[v0].add((v1, label))
#         self.backward_edges[v1].add((v0, label))
        
#     def join_vertices(self, v0: str, v1: str):
#         if v0 not in self.vertices:
#             raise ValueError(f"Vertex {v0} not in graph")
#         if v1 not in self.vertices:
#             raise ValueError(f"Vertex {v1} not in graph")
#         self.vertices.remove(v1)
#         for (v, label) in self.forward_edges[v1]:
#             self.forward_edges[v0].append((v, label))
#             self.backward_edges[v].remove((v1, label))
#             self.backward_edges[v].append((v0, label))
#         for (v, label) in self.backward_edges[v1]:
#             self.backward_edges[v0].append((v, label))
#             self.forward_edges[v].remove((v1, label))
#             self.forward_edges[v].append((v0, label))
#         self.forward_edges.pop(v1)
#         self.backward_edges.pop(v1)
#         self.edges = [(v0, v, label) for (v0, v, label) in self.edges if v != v1]


# class SubgroupOfFreeGroup:
#     def __init__(self, free_group: FreeGroup, rels: List[FreeGroupElement]):
#         for rel in rels:
#             if rel.free_group != free_group:
#                 raise ValueError(f"Relation {rel} is not in free group {self.free_group}")
#         self.free_group = free_group
#         self.rels = rels

    