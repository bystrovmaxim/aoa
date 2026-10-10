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

def _sample_with_specialization_edges() -> dict:
    """
    A graph carrying both directions of one axis, as the engine emits them.

    The head reaches its alternative through `entity_specialization`, an **association**; the
    extension reaches the head through `parent_entity`, a **generalization**. Both are real edges of
    the same model, and the full graph is expected to keep exactly one of them.
    """
    return {
        "schema_version": "1.0",
        "nodes": [
            {"id": "d.demo", "type": "Domain", "label": "Demo", "properties": {"name": "Demo", "description": ""}},
            {"id": "e.Head", "type": "Entity", "label": "Head", "properties": {"description": "head"}},
            {"id": "e.Alt", "type": "Entity", "label": "Alt", "properties": {"description": "alt"}},
        ],
        "edges": [
            {
                "source_id": "e.Head",
                "target_id": "d.demo",
                "type": "domain",
                "relationship": "Composition",
                "is_dag": False,
            },
            {
                "source_id": "e.Head",
                "target_id": "e.Alt",
                "type": "entity_specialization",
                "relationship": "Association",
                "is_dag": False,
                "properties": {
                    "field_name": "pack",
                    "classifier_field": "media",
                    "classifier_value": "first",
                    "alternative_index": 0,
                    "alternatives": ["first -> e.Alt"],
                    "labels": ["Alt (first)"],
                    "relation_type": "specialization",
                    "cardinality": "one",
                    "description": "d",
                    "has_inverse": True,
                    "deprecated": False,
                },
            },
            {
                "source_id": "e.Alt",
                "target_id": "e.Head",
                "type": "parent_entity",
                "relationship": _GEN,
                "is_dag": False,
                "properties": {
                    "field_name": "record",
                    "inverse_field": "pack",
                    "classifier_value": "first",
                    "head_entity_id": "e.Head",
                },
            },
        ],
    }


def test_the_two_directions_reach_the_store() -> None:
    """Both are stored: the exclusion happens when the payload is built, not when rows are written."""
    duck = DuckDBGraphResource.build_from_json(_sample_with_specialization_edges())
    con = duck.service

    assert int(con.execute("SELECT COUNT(*) FROM entity_specialization_edges").fetchone()[0]) == 1
    assert int(con.execute("SELECT COUNT(*) FROM parent_entity_edges").fetchone()[0]) == 1


def test_full_graph_keeps_the_axis_and_omits_the_generalization() -> None:
    """
    The exclusion is asserted rather than inherited by accident.

    The full graph is a system view: it strips generalization because inheritance is structure. The
    axis itself is an association, so it stays — which means one model produces two edges and the
    viewer is expected to keep exactly one of them. A change that made the axis a generalization
    would silently empty this diagram of it, and this test is what would say so.
    """
    duck = DuckDBGraphResource.build_from_json(_sample_with_specialization_edges())
    payload = _build_payload_from_duckdb(duck, _LIST_DOMAINS_DISTINCT_COLORS)

    kinds = [edge["data"]["edge_type"] for edge in payload["edges"]]  # type: ignore[index]
    assert "entity_specialization_edges" in kinds, "the axis reaches the system view"
    assert "parent_entity_edges" not in kinds, "and its reverse direction does not"
    assert kinds.count("entity_specialization_edges") == 1
    assert kinds.count("domain_edges") == 1, "no ordinary edge was dropped along with it"
