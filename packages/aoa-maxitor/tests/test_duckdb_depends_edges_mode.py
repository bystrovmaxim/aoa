# tests/maxitor/test_duckdb_depends_edges_mode.py
"""``depends_edges.mode`` column and ``edges`` payload for ``@depends`` wire metadata."""

from __future__ import annotations

import json
from typing import Any, cast

from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource


def _minimal_depends_payload(*, with_mode: str | None) -> dict:
    props_peer: dict[str, str] = {"description": "peer action"}
    if with_mode is not None:
        props_peer["mode"] = with_mode
    return {
        "schema_version": "1.0",
        "nodes": [
            {"id": "a.host", "type": "Action", "label": "Host", "properties": {"description": "host"}},
            {"id": "a.peer", "type": "Action", "label": "Peer", "properties": {"description": "peer"}},
            {
                "id": "r.pay",
                "type": "Resource",
                "label": "Pay",
                "properties": {"description": "gateway"},
            },
        ],
        "edges": [
            {
                "source_id": "a.host",
                "target_id": "a.peer",
                "type": "@depends",
                "relationship": "Association",
                "is_dag": True,
                "properties": props_peer,
            },
            {
                "source_id": "a.host",
                "target_id": "r.pay",
                "type": "@depends",
                "relationship": "Association",
                "is_dag": True,
                "properties": {"description": "payment resource"},
            },
        ],
    }


def test_depends_edges_stores_mode_column() -> None:
    duck = DuckDBGraphResource.build_from_json(_minimal_depends_payload(with_mode="include"))
    rows = duck.execute_fetch_dicts(
        "SELECT target_id, description, mode FROM depends_edges ORDER BY target_id",
    )
    assert len(rows) == 2
    assert rows[0]["target_id"] == "a.peer"
    assert rows[0]["description"] == "peer action"
    assert rows[0]["mode"] == "include"
    assert rows[1]["target_id"] == "r.pay"
    assert rows[1]["description"] == "payment resource"
    assert rows[1]["mode"] is None


def test_edges_view_payload_includes_mode_json() -> None:
    duck = DuckDBGraphResource.build_from_json(_minimal_depends_payload(with_mode="extend"))
    payloads = duck.execute_fetch_dicts(
        "SELECT payload FROM edges WHERE type = 'depends_edges' ORDER BY target_id",
    )
    assert len(payloads) == 2

    def _as_obj(raw: object) -> dict[str, Any]:
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)
        return json.loads(str(raw))

    p0 = _as_obj(payloads[0]["payload"])
    p1 = _as_obj(payloads[1]["payload"])
    assert p0 == {"description": "peer action", "mode": "extend"}
    assert p1["description"] == "payment resource"
    assert p1.get("mode") is None
