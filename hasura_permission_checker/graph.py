from __future__ import annotations
from dataclasses import dataclass, field
from itertools import chain
from typing import Any, Literal
from pyvis.network import Network


@dataclass
class Edge:
    node_from: Node
    node_to: Node
    relationship: Literal["1:1", "1:N", "N:N"]
    filter_on: dict[str, Any] = field(default_factory=dict)
    attrs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.node_from, self.node_to))

    def __repr__(self) -> str:
        return f"Edge({self.node_from} -> {self.node_to})"


@dataclass
class Node:
    name: str
    role: str
    is_root: bool
    available_roles: list[str] = field(default_factory=list)
    permissions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    edges_before: set[Edge] = field(default_factory=set)
    edges_after: set[Edge] = field(default_factory=set)

    @property
    def nid(self) -> int:
        """Graphiz need a numerical node id."""
        return self.__hash__()

    @property
    def filter_on(self) -> dict[str, Any]:
        return self.permissions.get("filter", {}).get("filter", {})

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return f"Node({self.name}, {self.role})"


@dataclass
class Graph:
    nodes: set[Node] = field(default_factory=set)
    edges: set[Edge] = field(default_factory=set)

    def add_node(self, n: Node):
        if n in self:
            raise ValueError(f"Node {n} already in graph")
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
            e_sym = Edge(
                node_from=e.node_to,
                node_to=e.node_from,
                relationship=e.relationship,
                filter_on=e.filter_on,
                metadata=e.metadata,
            )
            self.add_edge(e_sym, symmetric=False)

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

    def get_node_by_name(self, name: str) -> Node:
        for n in self.nodes:
            if n.name == name:
                return n
        raise ValueError(f"Node with name {name} not found.")

    def get_node_by_id(self, nid: int) -> Node:
        for n in self.nodes:
            if n.nid == nid:
                return n
        raise ValueError(f"Node with id {nid} not found.")

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
            if n.is_root:
                continue
            if not n.edges_before and not n.edges_after:
                print("removing isolated node", n)
                self.remove_node(n)
                nodes_removed.append(n)
        return nodes_removed

    def prune_intermediary_nodes(self):
        nodes_removed = []
        for n in set(self.nodes):
            if n.is_root:
                continue
            nodes_before, nodes_after = self.neighbors(n)
            if len(nodes_before) == 2 and nodes_before == nodes_after:
                n1 = nodes_before.pop()
                n2 = nodes_before.pop()
                e = Edge(
                    node_from=n1,
                    node_to=n2,
                    relationship="N:N",
                    filter_on=n1.filter_on,
                )
                self.add_edge(e, symmetric=True)
                self.remove_node(n)
                nodes_removed.append(n)
                print("removing node", n, "connecting", n1, "with", n2)

        return nodes_removed

    def show(self) -> Network:
        net = Network(
            notebook=True,
            cdn_resources="remote",
            neighborhood_highlight=True,
            select_menu=True,
            directed=True,
            layout=True,
            filter_menu=True,
        )

        # set the physics layout of the network
        net.barnes_hut()

        for n in self.nodes:
            e_from, e_to = self.neighbors(n)
            n_neighbours = len(e_from) + len(e_to)
            n_size = 20 + min(n_neighbours, 20)
            color = "red" if n.is_root else "blue"
            net.add_node(
                n_id=n.nid,
                name=n.name,
                title=n.name,
                size=n_size,
                color=color,
            )

        for e in self.edges:
            net.add_edge(
                e.node_from.nid,
                e.node_to.nid,
                arrows={"from": True},
                arrowStrikethrough=True,
            )
        net.toggle_physics(False)
        net.show_buttons(filter_=["physics"])
        return net

    def __contains__(self, key: Node | Edge) -> bool:
        if isinstance(key, Node):
            return key in self.nodes
        if isinstance(key, Edge):
            return key in self.edges
        return False
