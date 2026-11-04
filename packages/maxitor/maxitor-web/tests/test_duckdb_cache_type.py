# packages/maxitor/maxitor-web/tests/test_duckdb_cache_type.py
"""
Maxitor knows the cache declarations and the entities they cache and invalidate (issue #412).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Protocol 1.4 adds the node type ``Cache`` and the edge types ``@cache_key``,
``@cache_read``, ``@cache_write``, ``@cache_invalidate``, ``caches`` and
``invalidates``. The store refuses a type it does not know, so each is taught: its
table, its rows, its place in the union views, the slug the client translates, a
colour and a glyph.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from maxitor.web.model.diagrams.actions.list_node_types_action import (
    NODE_TYPE_FILL_COLORS,
    interchange_node_type_from_duck,
)
from maxitor.web.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_ICONS = Path(__file__).resolve().parents[1] / "client" / "src" / "lib" / "icons" / "graph_node_disk_icons.ts"

_GET = "shop.GetOrderAction"
_UPDATE = "shop.UpdateOrderAction"
_ORDER = "shop.OrderCoreEntity"
_EDGE_TABLES = {
    "@cache_key": "cache_key_edges",
    "@cache_read": "cache_read_edges",
    "@cache_write": "cache_write_edges",
    "@cache_invalidate": "cache_invalidate_edges",
    "caches": "caches_edges",
    "invalidates": "invalidates_edges",
}


def _edge(source: str, target: str, edge_type: str, relationship: str) -> dict[str, Any]:
    return {"source_id": source, "target_id": target, "type": edge_type, "relationship": relationship, "is_dag": False}


def _graph() -> dict[str, Any]:
    """A reader with a key, a read and a write, and an updater with an invalidation, of one order."""
    nodes = [
        {"id": _GET, "type": "Action", "label": "GetOrderAction", "properties": {"description": "Get"}},
        {"id": _UPDATE, "type": "Action", "label": "UpdateOrderAction", "properties": {"description": "Update"}},
    ]
    edges = []
    for owner, kind in ((_GET, "key"), (_GET, "read"), (_GET, "write"), (_UPDATE, "invalidate")):
        node_id = f"{owner}:order_cache_{kind}"
        nodes.append({"id": node_id, "type": "Cache", "label": f"order_cache_{kind}", "properties": {"kind": kind, "description": kind.title()}})
        edges.append(_edge(owner, node_id, f"@cache_{kind}", "Composition"))
    edges += [_edge(_GET, _ORDER, "caches", "Association"), _edge(_UPDATE, _ORDER, "invalidates", "Association")]
    return {"schema_version": "1.4", "nodes": nodes, "edges": edges}


def _rows(duck: DuckDBGraphResource, sql: str) -> list[tuple[Any, ...]]:
    return [tuple(row) for row in duck.service.execute(sql).fetchall()]


def test_the_cache_nodes_land_in_their_table() -> None:
    """Each declaration is a row with its kind and description."""
    duck = DuckDBGraphResource.build_from_json(_graph())
    assert _rows(duck, "SELECT label, kind, description FROM cache ORDER BY label") == [
        ("order_cache_invalidate", "invalidate", "Invalidate"),
        ("order_cache_key", "key", "Key"),
        ("order_cache_read", "read", "Read"),
        ("order_cache_write", "write", "Write"),
    ]


@pytest.mark.parametrize(("edge_type", "table"), sorted(_EDGE_TABLES.items()))
def test_each_new_edge_lands_in_its_own_table(edge_type: str, table: str) -> None:
    """Every new edge type has its table and its place in the edges view."""
    duck = DuckDBGraphResource.build_from_json(_graph())
    assert _rows(duck, f"SELECT COUNT(*) FROM {table}") == [(1,)]
    assert table in {row[0] for row in _rows(duck, "SELECT DISTINCT type FROM edges")}


def test_the_node_view_carries_the_cache_kind() -> None:
    """The union view reports the slug and the payload the client reads."""
    duck = DuckDBGraphResource.build_from_json(_graph())
    payloads = _rows(duck, "SELECT payload FROM nodes WHERE type = 'cache' ORDER BY id")
    assert len(payloads) == 4
    assert '"kind":"write"' in str(payloads).replace(" ", "")


def test_the_client_can_draw_it() -> None:
    """Slug, a colour of its own and a glyph."""
    assert interchange_node_type_from_duck("cache") == "Cache"
    assert list(NODE_TYPE_FILL_COLORS.values()).count(NODE_TYPE_FILL_COLORS["Cache"]) == 1
    assert "\n  Cache:" in _ICONS.read_text(encoding="utf-8")
