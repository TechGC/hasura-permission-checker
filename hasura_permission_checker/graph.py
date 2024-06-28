from __future__ import annotations
from dataclasses import dataclass, field
from itertools import chain
from typing import Any


@dataclass
class Edge:
    node_from: Node
    node_to: Node

    def __hash__(self) -> int:
        return hash((self.node_from.nid, self.node_to.nid))

    def __repr__(self) -> str:
        return f"Edge({self.node_from} -> {self.node_to})"


@dataclass
class Node:
    nid: int
    label: str
    title: str
    attrs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    edges_before: set[Edge] = field(default_factory=set)
    edges_after: set[Edge] = field(default_factory=set)

    def contribute_to_permissions(self) -> bool:
        if self.has_attr("is_root", "True"):
            return True
        return False

    def has_attr(self, key: str, value) -> bool:
        attrs = {**self.attrs, "title": self.title, "label": self.label}
        return key in self.attrs and attrs[key] == value

    def __hash__(self) -> int:
        return self.nid

    def __repr__(self) -> str:
        return f"Node({self.nid}, {self.label})"


@dataclass
class Graph:
    nodes: set[Node] = field(default_factory=set)
    edges: set[Edge] = field(default_factory=set)

    def add_node(self, n: Node):
        self.nodes.add(n)

    def add_edge(self, e: Edge, symmetric: bool = False):
        if e.node_from not in self:
            self.add_node(e.node_from)
        if e.node_to not in self:
            self.add_node(e.node_to)

        self.edges.add(e)
        e.node_from.edges_after.add(e)
        e.node_to.edges_before.add(e)
        if symmetric:
            e = Edge(e.node_to, e.node_from)
            self.add_edge(e, symmetric=False)

    def remove_node(self, n: Node):
        if n not in self:
            raise ValueError(f"Node {n} not found in graph")
        for e in list(chain(n.edges_before, n.edges_after)):
            self.remove_edge(e)
        self.nodes.remove(n)

    def remove_edge(self, e: Edge):
        e.node_from.edges_after.remove(e)
        e.node_to.edges_before.remove(e)
        self.edges.remove(e)

    def get_nodes_by_attr(self, key: str, value: Any) -> list[Node]:
        return [n for n in self.nodes if n.has_attr(key, value)]

    def get_node_by_label(self, label: str) -> Node:
        for n in self.nodes:
            if n.label == label:
                return n
        raise ValueError(f"Node with label {label} not found")

    def get_node_by_id(self, nid: int) -> Node:
        for n in self.nodes:
            if n.nid == nid:
                return n
        raise ValueError(f"Node with id {nid} not found")

    @staticmethod
    def neighbors(node: Node) -> tuple[set[Node], set[Node]]:
        nodes_before = {e.node_from for e in node.edges_before}
        nodes_after = {e.node_to for e in node.edges_after}
        return nodes_before, nodes_after

    def prune(self) -> list[Node]:
        removed = self.prune_intermediary_nodes()
        removed += self.prune_isolated_nodes()
        return removed

    def prune_isolated_nodes(self) -> list[Node]:
        nodes_removed = []
        for n in set(self.nodes):
            if n.contribute_to_permissions():
                continue
            if not n.edges_before and not n.edges_after:
                print("removing isolated node", n)
                self.remove_node(n)
                nodes_removed.append(n)
        return nodes_removed

    def prune_intermediary_nodes(self):
        nodes_removed = []
        for n in set(self.nodes):
            if n.contribute_to_permissions():
                continue
            nodes_before, nodes_after = self.neighbors(n)
            if len(nodes_before) == 2 and nodes_before == nodes_after:
                n1 = nodes_before.pop()
                n2 = nodes_before.pop()
                self.add_edge(Edge(n1, n2), symmetric=True)
                self.remove_node(n)
                nodes_removed.append(n)
                print("removing node", n, "connecting", n1, "with", n2)

        return nodes_removed

    def __contains__(self, key: Node | Edge) -> bool:
        if isinstance(key, Node):
            return key in self.nodes
        if isinstance(key, Edge):
            return key in self.edges
        return False



