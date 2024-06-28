import json
from typing import Any

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
            node = Node(name=t_name, title=t_name, attrs=attrs)
            g.add_node(node)

        # Create edges
        for t in tables:
            t_name = t["table"]["name"]
            src = g.get_node_by_name(t_name)

            for r in t.get("array_relationships", []):
                r_to = r["using"]["foreign_key_constraint_on"]["table"]["name"]
                try:
                    dst = g.get_node_by_name(r_to)
                except ValueError:
                    print(f"Ignoring invalid array relationship: {t_name} -> {r_to}")
                    continue
                edge = Edge(node_from=src, node_to=dst)
                g.add_edge(edge)

            for r in t.get("object_relationships", []):
                r_to = r["name"]
                try:
                    dst = g.get_node_by_name(r_to)
                except ValueError:
                    print(f"Ignoring invalid array relationship: {t_name} -> {r_to}")
                    continue
                edge = Edge(node_from=src, node_to=dst)
                g.add_edge(edge)

        return g

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
