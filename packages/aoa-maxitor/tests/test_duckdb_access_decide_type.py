# packages/aoa-maxitor/tests/test_duckdb_access_decide_type.py
"""
Maxitor knows the access check as a graph type of its own (FR-018).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A graph carrying ``AccessDecide`` used to be refused outright: the resource keeps a list
of known node and edge types and raises on anything else, which is the right behaviour
for a viewer that must not silently drop what it cannot draw. The type therefore has to
be taught: its own table and its own rows, its edge alongside the other declarations, the
slug translated for the client with a colour of its own, and a glyph to draw.

The last test feeds the same resource a type nobody declared: the guard must still refuse,
so the tests above prove the type was taught rather than the guard loosened.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTheTypeIsKnown      — the graph is accepted, and its rows land where they should
TestItReachesTheClient  — slug, colour and glyph are all in place
TestTheGuardStillWorks  — a type nobody declared is still refused
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aoa.maxitor.model.diagrams.actions.list_node_types_action import (
    NODE_TYPE_FILL_COLORS,
    interchange_node_type_from_duck,
)
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_ICONS = (
    Path(__file__).resolve().parents[1] / "client" / "src" / "lib" / "icons" / "graph_node_disk_icons.ts"
)

_NODE = "a.CancelOrderAction:cancel_order_access_decide"
_ACTION = "a.CancelOrderAction"


def _graph() -> dict:
    """A graph carrying one access check and the edge that attaches it, as the engine emits it."""
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": _ACTION,
                "type": "Action",
                "label": "CancelOrderAction",
                "properties": {"description": "Cancel an order"},
            },
            {
                "id": _NODE,
                "type": "AccessDecide",
                "label": "cancel_order_access_decide",
                "properties": {},
            },
        ],
        "edges": [
            {
                "source_id": _ACTION,
                "target_id": _NODE,
                "type": "@access_decide",
                "relationship": "Composition",
                "is_dag": False,
            }
        ],
    }


def _count(con: object, sql: str) -> int:
    """One scalar count out of the graph database."""
    return int(con.execute(sql).fetchone()[0])  # type: ignore[attr-defined]


class TestTheTypeIsKnown:
    def test_a_graph_carrying_the_check_is_accepted(self) -> None:
        duck = DuckDBGraphResource.build_from_json(_graph())

        assert _count(duck.service, "SELECT COUNT(*) FROM access_decide") == 1

    def test_its_rows_carry_what_the_client_draws(self) -> None:
        duck = DuckDBGraphResource.build_from_json(_graph())

        row = duck.service.execute("SELECT id, label, description FROM access_decide").fetchone()

        assert row[0] == _NODE
        assert row[1] == "cancel_order_access_decide"

    def test_the_edge_lands_in_its_own_table(self) -> None:
        duck = DuckDBGraphResource.build_from_json(_graph())

        assert _count(duck.service, "SELECT COUNT(*) FROM access_decide_edges") == 1
        types = {r[0] for r in duck.service.execute("SELECT DISTINCT type FROM edges").fetchall()}
        assert "access_decide_edges" in types

    def test_the_node_view_reports_the_type_the_client_translates(self) -> None:
        duck = DuckDBGraphResource.build_from_json(_graph())

        types = {r[0] for r in duck.service.execute("SELECT DISTINCT type FROM nodes").fetchall()}

        assert "access_decide" in types

    def test_its_indexes_exist_like_every_other_edge_table(self) -> None:
        """The edge tables are indexed through one list; a missing entry would slow the viewer."""
        duck = DuckDBGraphResource.build_from_json(_graph())

        indexes = {
            r[0]
            for r in duck.service.execute(
                "SELECT index_name FROM duckdb_indexes() WHERE table_name = 'access_decide_edges'"
            ).fetchall()
        }

        assert indexes == {"ix_access_decide_edges_source", "ix_access_decide_edges_target"}


class TestItReachesTheClient:
    def test_the_slug_has_an_interchange_type(self) -> None:
        assert interchange_node_type_from_duck("access_decide") == "AccessDecide"

    def test_the_type_has_a_colour_of_its_own(self) -> None:
        own = NODE_TYPE_FILL_COLORS["AccessDecide"]

        assert own == "#984EA3"
        assert list(NODE_TYPE_FILL_COLORS.values()).count(own) == 1

    def test_the_client_has_a_glyph_for_it(self) -> None:
        """The client map is TypeScript, so it is read as text: the type must be a key."""
        source = _ICONS.read_text(encoding="utf-8")

        assert "\n  AccessDecide:" in source


class TestTheGuardStillWorks:
    def test_a_type_nobody_declared_is_still_refused(self) -> None:
        graph = _graph()
        graph["nodes"][1]["type"] = "NotADeclaredType"

        with pytest.raises(KeyError, match="Unknown nodes graph type"):
            DuckDBGraphResource.build_from_json(graph)

    def test_an_edge_type_nobody_declared_is_still_refused(self) -> None:
        graph = _graph()
        graph["edges"][0]["type"] = "@not_declared"

        with pytest.raises(KeyError, match="Unknown edge graph type"):
            DuckDBGraphResource.build_from_json(graph)
