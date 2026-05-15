# tests/maxitor/test_full_graph_payload_shape.py
"""Smoke: full-graph payload node/edge ``data`` matches slim contract (PR-1 + PR-2)."""

from __future__ import annotations

from typing import Any

from aoa.maxitor.model.diagrams.actions.full_graph_action import _build_payload_from_duckdb
from aoa.maxitor.model.diagrams.actions.list_domains_action import _LIST_DOMAINS_DISTINCT_COLORS

# PR-1/PR-2 slim contract — keys that must not appear in ``nodes[i].data`` / ``edges[i].data``.
_FORBIDDEN_NODE_DATA = frozenset(
    {
        "payload",
        "graph_key",
        "qualified",
        "typeFill",
        "graph_node_subtitle",
        "isDagCycleViolationIncident",
    },
)
_FORBIDDEN_EDGE_DATA = frozenset(
    {
        "payload",
        "isDag",
        "sourceAttachment",
        "targetAttachment",
        "lineStyle",
        "isForbiddenDagCycle",
        "relationshipName",
    },
)


class _RowsDuck:
    """Minimal stand-in for ``DuckDBGraphResource`` returning prebuilt SQL row dicts."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def execute_fetch_dicts(self, _sql: str) -> list[dict[str, Any]]:
        return list(self._rows)


def test_build_full_graph_payload_pr1_slim_shape() -> None:
    rows: list[dict[str, Any]] = [
        {
            "result_type": "nodes",
            "pk": "dom.x",
            "label": "dom.x",
            "type": "domain",
            "idx": None,
            "source_id": None,
            "target_id": None,
            "relationship": None,
            "is_dag": None,
            "payload": None,
        },
        {
            "result_type": "nodes",
            "pk": "pkg.A",
            "label": "pkg.A",
            "type": "action",
            "idx": None,
            "source_id": None,
            "target_id": None,
            "relationship": None,
            "is_dag": None,
            "payload": None,
        },
        {
            "result_type": "edges",
            "pk": "0",
            "label": None,
            "type": "field",
            "idx": 0,
            "source_id": "dom.x",
            "target_id": "pkg.A",
            "relationship": "composition",
            "is_dag": None,
            "payload": None,
        },
        {
            "result_type": "domain",
            "pk": "dom.x",
            "label": None,
            "type": None,
            "idx": None,
            "source_id": None,
            "target_id": None,
            "relationship": None,
            "is_dag": None,
            "payload": None,
        },
    ]
    payload = _build_payload_from_duckdb(_RowsDuck(rows), _LIST_DOMAINS_DISTINCT_COLORS)

    assert payload["title"] == "Interchange graph"
    for key in ("nodes", "edges", "legend_items", "node_type_map", "domain_color_map", "constants", "bubble_plugins"):
        assert key in payload

    for node in payload["nodes"]:
        data = node.get("data") or {}
        overlap = _FORBIDDEN_NODE_DATA & data.keys()
        assert not overlap, f"unexpected node.data keys: {overlap}"

    for edge in payload["edges"]:
        data = edge.get("data") or {}
        overlap = _FORBIDDEN_EDGE_DATA & data.keys()
        assert not overlap, f"unexpected edge.data keys: {overlap}"
        assert "label" in data
        assert "edge_type" in data
