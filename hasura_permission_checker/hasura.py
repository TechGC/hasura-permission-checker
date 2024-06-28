import json
from typing import Any

from pyvis.network import Network

from hasura_permission_checker.graph import Graph, Node, Edge


class HasuraParser:

    @staticmethod
    def read_metadata(filename: str) -> dict[str, Any]:
        with open(filename) as f:
            metadata = json.loads(f.read())
        return metadata

    def generate_graph(self, filename: str) -> Graph:

        g = Graph()
        metadata = self.read_metadata(filename)
        tables = [i for i in metadata["sources"][0]["tables"]]

        # Create nodes
        for nid, t in enumerate(tables):
            t_name = t["table"]["name"]
            attrs = {
                "role": self._get_table_role(t),
                "is_root": str(self._is_root_table(t)),
            }
            node = Node(nid=nid, label=t_name, title=t_name, attrs=attrs)
            g.add_node(node)

        # Create edges
        for t in tables:
            t_name = t["table"]["name"]
            src = g.get_node_by_label(t_name)

            for r in t.get("array_relationships", []):
                r_to = r["using"]["foreign_key_constraint_on"]["table"]["name"]
                try:
                    dst = g.get_node_by_label(r_to)
                except ValueError:
                    print(f"Ignoring invalid array relationship: {t_name} -> {r_to}")
                    continue
                edge = Edge(node_from=src, node_to=dst)
                g.add_edge(edge)

            for r in t.get("object_relationships", []):
                r_to = r["name"]
                try:
                    dst = g.get_node_by_label(r_to)
                except ValueError:
                    print(f"Ignoring invalid array relationship: {t_name} -> {r_to}")
                    continue
                edge = Edge(node_from=src, node_to=dst)
                g.add_edge(edge)

        return g

    @staticmethod
    def generate_network(g: Graph) -> Network:
        net = Network(
            notebook=True,
            cdn_resources="remote",
            neighborhood_highlight=True,
            select_menu=True,
            directed=True,
            layout=True,
            filter_menu=True
        )

        # set the physics layout of the network
        net.barnes_hut()

        for n in g.nodes:
            e_from, e_to = g.neighbors(n)
            n_neighbours = len(e_from) + len(e_to)
            n_size = 20 + min(n_neighbours, 20)
            color = "red" if n.has_attr("is_root", "True") else "blue"
            border = "yellow" if n.has_attr("role", "public_role") else "blue"
            net.add_node(
                n.nid,
                label=n.label,
                title=n.title,
                size=n_size,
                color=color,
                **n.attrs,
            )

        for e in g.edges:
            net.add_edge(
                e.node_from.nid,
                e.node_to.nid,
                arrows={"from": True},
                arrowStrikethrough=True,
            )
        net.toggle_physics(False)
        net.show_buttons(filter_=["physics"])
        return net

    @staticmethod
    def _get_table_role(table: dict[str, Any]) -> str | None:
        for sp in table.get("select_permissions", []):
            if role := sp.get("role"):
                return role
        return None

    @staticmethod
    def _is_root_table(table: dict[str, Any]) -> bool:
        for sp in table.get("select_permissions", []):
            qrf = sp["permission"].get("query_root_fields")
            srf = sp["permission"].get("subscription_root_fields")

            if qrf is None and srf is None:
                return True
            # TODO implement the case where the fields had ["select"]
            if isinstance(qrf, list) and len(qrf) > 1:
                return True
            if isinstance(srf, list) and len(qrf) > 1:
                return True
        return False
