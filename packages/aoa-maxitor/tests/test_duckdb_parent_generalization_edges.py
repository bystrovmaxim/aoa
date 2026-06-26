# tests/maxitor/test_duckdb_parent_generalization_edges.py
"""PR-7: DuckDB stores ``parent_*`` generalization edges; full-graph SQL omits them from the viewer."""

from __future__ import annotations

from aoa.action_machine.graph.core.edge_relationship import GENERALIZATION
from aoa.maxitor.model.diagrams.actions.full_graph_action import _build_payload_from_duckdb
from aoa.maxitor.model.diagrams.actions.list_domains_action import _LIST_DOMAINS_DISTINCT_COLORS
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_GEN = GENERALIZATION.archimate_name


def _sample_with_parent_edges() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {"id": "d.child", "type": "Domain", "label": "ChildDom", "properties": {"name": "C", "description": ""}},
            {"id": "d.parent", "type": "Domain", "label": "ParentDom", "properties": {"name": "P", "description": ""}},
            {"id": "r.Child", "type": "Role", "label": "ChildRole", "properties": {"role_mode": "check"}},
            {"id": "r.Parent", "type": "Role", "label": "ParentRole", "properties": {"role_mode": "check"}},
            {"id": "a.Child", "type": "Action", "label": "ChildAct", "properties": {"description": "c"}},
            {"id": "a.Parent", "type": "Action", "label": "ParentAct", "properties": {"description": "p"}},
        ],
        "edges": [
            {
                "source_id": "d.child",
                "target_id": "d.parent",
                "type": "parent_domain",
                "relationship": _GEN,
                "is_dag": False,
            },
            {
                "source_id": "r.Child",
                "target_id": "r.Parent",
                "type": "parent_role",
                "relationship": _GEN,
                "is_dag": False,
            },
            {
                "source_id": "a.Child",
                "target_id": "a.Parent",
                "type": "parent_action",
                "relationship": _GEN,
                "is_dag": False,
            },
            {
                "source_id": "a.Child",
                "target_id": "d.child",
                "type": "domain",
                "relationship": "Composition",
                "is_dag": False,
            },
        ],
    }


def test_duckdb_parent_edge_tables_and_edges_view() -> None:
    duck = DuckDBGraphResource.build_from_json(_sample_with_parent_edges())
    con = duck.service

    def _count(sql: str) -> int:
        return int(con.execute(sql).fetchone()[0])

    assert _count("SELECT COUNT(*) FROM parent_domain_edges") == 1
    assert _count("SELECT COUNT(*) FROM parent_role_edges") == 1
    assert _count("SELECT COUNT(*) FROM parent_action_edges") == 1
    assert _count("SELECT COUNT(*) FROM domain_edges") == 1

    types = {r[0] for r in con.execute("SELECT DISTINCT type FROM edges").fetchall()}
    assert "parent_domain_edges" in types
    assert "parent_role_edges" in types
    assert "parent_action_edges" in types
    assert "domain_edges" in types


def test_full_graph_payload_omits_generalization_edges() -> None:
    duck = DuckDBGraphResource.build_from_json(_sample_with_parent_edges())
    payload = _build_payload_from_duckdb(duck, _LIST_DOMAINS_DISTINCT_COLORS)

    assert len(payload["edges"]) == 1
    e0 = payload["edges"][0]
    assert e0["source"] == "a.Child"
    assert e0["target"] == "d.child"
    assert e0["data"]["label"] == "Composition"  # type: ignore[index]
    assert e0["data"]["edge_type"] == "domain_edges"  # type: ignore[index]
