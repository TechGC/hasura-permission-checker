import itertools
import json
from typing import Any

from hasura_permission_checker.graph import Graph, Node, Edge


class HasuraParser:

    @staticmethod
    def read_metadata(filename: str) -> dict[str, Any]:
        with open(filename) as f:
            metadata = json.loads(f.read())
        return metadata

    def generate_all_graph(self, filename: str, role: str) -> list[Graph]:
        metadata = self.read_metadata(filename)
        tables = [i for i in metadata["sources"][0]["tables"]]
        available_roles = self._get_available_roles(tables)
        pass

    def generate_graph(self, filename: str, role: str) -> Graph:
        g = Graph()
        metadata = self.read_metadata(filename)
        tables = [i for i in metadata["sources"][0]["tables"]]

        # Create nodes
        node_not_included = set()
        for nid, t in enumerate(tables):
            t_name = t["table"]["name"]
            if not (permissions := self._get_selection_permissions(t, role)):
                node_not_included.add(t_name)
                continue
            node = Node(
                name=t_name,
                available_roles=self._get_table_roles(t),
                permissions=permissions,
                metadata=t,
                is_root=self._is_root_table(t, role),
                role=role,
            )
            g.add_node(node)

        # Create edges
        for t in tables:
            t_name = t["table"]["name"]
            try:
                node_from = g.get_node_by_name(t_name)
            except ValueError:
                # Node wasn't added because it has no permissions
                continue

            relationships = itertools.chain(
                t.get("array_relationships", []),
                t.get("object_relationships", [])
            )
            for r in relationships:
                try:
                    # array relationship
                    r_to = r["using"]["foreign_key_constraint_on"]["table"]["name"]
                    r_type = "1:N"
                except (TypeError, KeyError):
                    # object relationship
                    r_type = "1:1"
                    r_to = r["name"]

                try:
                    node_to = g.get_node_by_name(r_to)
                except ValueError:
                    if r_to not in node_not_included:
                        print(f"Skipping edge: unknown table {r_to} referenced by {t_name}.")
                    continue

                edge = Edge(
                    node_from=node_from,
                    node_to=node_to,
                    relationship=r_type,
                    filter_on=node_from.filter_on,
                    metadata=r,
                )

                g.add_edge(edge)

        return g

    @staticmethod
    def _get_selection_permissions(table: dict[str, Any], role: str) -> dict[str, Any]:
        for sp in table.get("select_permissions", []):
            if sp.get("role") == role:
                return sp.get("permission", {})
        return {}

    @staticmethod
    def _get_table_roles(table: dict[str, Any]) -> list[str]:
        return [r for sp in table.get("select_permissions", []) if (r := sp.get("role"))]

    @classmethod
    def _get_available_roles(cls, tables: list[dict[str, Any]]) -> set[str]:
        return set(r for t in tables for r in cls._get_table_roles(t))

    @classmethod
    def _is_root_table(cls, table: dict[str, Any], role: str) -> bool:
        permission = cls._get_selection_permissions(table, role)
        if not permission:
            # no permission defined, everything is allowed
            return True

        qrf = permission.get("query_root_fields")
        srf = permission.get("subscription_root_fields")

        if qrf is None and srf is None:
            # no permission defined, everything is allowed
            return True

        # If there is a list and it is not empty, return True
        # TODO implement the case where the fields had ["select"]
        if isinstance(qrf, list) and len(qrf) > 1:
            return True
        if isinstance(srf, list) and len(srf) > 1:
            return True

        return False

