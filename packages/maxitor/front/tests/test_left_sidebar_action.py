# tests/maxitor/test_left_sidebar_action.py
"""Tests for GetLeftMenuSidebarDataAction — one test group per aspect."""

from __future__ import annotations

from maxitor.front.model.core.actions.left_sidebar_action import (
    _ROOT_SECTIONS,
    GetLeftMenuSidebarDataAction,
)
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

from aoa.action_machine.model import BaseState

_ACTION = GetLeftMenuSidebarDataAction()

# ─── Coordinator fixtures ─────────────────────────────────────────────────────

_DOMAIN_ONLY = {
    "nodes": [
        {"id": "dom.billing", "type": "Domain", "label": "Billing", "properties": {"name": "Billing", "description": ""}},
    ],
    "edges": [],
}

_ENTITY_WITH_LIFECYCLE = {
    "nodes": [
        {"id": "ent.order", "type": "Entity", "label": "Order", "properties": {"description": "", "entity_kind": "core"}},
        {"id": "lc.status", "type": "Lifecycle", "label": "order_status_lifecycle", "properties": {"field_name": "order_status"}},
    ],
    "edges": [
        {
            "source_id": "ent.order",
            "target_id": "lc.status",
            "type": "lifecycle",
            "relationship": "Composition",
            "is_dag": False,
            "properties": {"field_name": "order_status"},
        },
    ],
}

_FULL_GRAPH = {
    "nodes": [
        {"id": "dom.billing", "type": "Domain", "label": "Billing", "properties": {"name": "Billing", "description": ""}},
        {"id": "dom.messaging", "type": "Domain", "label": "Messaging", "properties": {"name": "Messaging", "description": ""}},
        {"id": "ent.order", "type": "Entity", "label": "Order", "properties": {"description": "", "entity_kind": "core"}},
        {"id": "ent.invoice", "type": "Entity", "label": "Invoice", "properties": {"description": "", "entity_kind": "core"}},
        {"id": "lc.status", "type": "Lifecycle", "label": "order_status_lifecycle", "properties": {"field_name": "order_status"}},
    ],
    "edges": [
        {
            "source_id": "ent.order",
            "target_id": "lc.status",
            "type": "lifecycle",
            "relationship": "Composition",
            "is_dag": False,
            "properties": {"field_name": "order_status"},
        },
    ],
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _duck(coordinator: dict) -> dict:
    return {DUCKDB_GRAPH_CONNECTION_KEY: DuckDBGraphResource.build_from_json(coordinator)}


# ─── Aspect 1: build_level1_aspect ───────────────────────────────────────────


async def test_level1_count() -> None:
    r = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    assert len(r["level1_nodes"]) == len(_ROOT_SECTIONS)


async def test_level1_order_and_types() -> None:
    r = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    for i, (root_id, label, type_) in enumerate(_ROOT_SECTIONS):
        n = r["level1_nodes"][i]
        assert n.id == root_id
        assert n.label == label
        assert n.type == type_
        assert n.parent_id is None


# ─── Aspect 2: build_level2_diagrams_aspect ──────────────────────────────────


async def test_level2_diagrams_count() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    assert len(r2["level2_diagrams"]) == 3


async def test_level2_diagrams_ids() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    assert {(n.id, n.parent_id, n.label, n.type) for n in r2["level2_diagrams"]} == {
        ("application_interchange_graph", "applications_root", "Full graph view", "graph"),
        ("application_all_erd", "applications_root", "ERD all domains view", "erd_all"),
        ("application_all_use_cases", "applications_root", "Use case all domains view", "use_case_all"),
    }


async def test_level2_diagrams_labels_have_view_suffix() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    for n in r2["level2_diagrams"]:
        assert n.label.endswith(" view"), n.label


def test_diagram_view_label_idempotent() -> None:
    assert _ACTION._diagram_view_label("Full graph") == "Full graph view"
    assert _ACTION._diagram_view_label("Full graph view") == "Full graph view"


async def test_level2_diagrams_sorted_alphabetically() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    labels = [n.label.lower() for n in r2["level2_diagrams"]]
    assert labels == sorted(labels)


async def test_level2_diagrams_passes_level1_through() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    assert r2["level1_nodes"] == r1["level1_nodes"]


# ─── Aspect 3: build_level2_nodes_aspect ─────────────────────────────────────


async def test_level2_nodes_domain_goes_to_domains_root() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    r3 = await _ACTION.build_level2_nodes_aspect(None, BaseState(**r2), None, _duck(_DOMAIN_ONLY))  # type: ignore[arg-type]
    assert len(r3["level2_nodes"]) == 1
    node = r3["level2_nodes"][0]
    assert node.id == "dom.billing"
    assert node.parent_id == "domains_root"
    assert node.type == "Domain"


async def test_level2_nodes_hold_only_domains() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    r3 = await _ACTION.build_level2_nodes_aspect(None, BaseState(**r2), None, _duck(_FULL_GRAPH))  # type: ignore[arg-type]
    assert {n.type for n in r3["level2_nodes"]} == {"Domain"}
    assert {n.parent_id for n in r3["level2_nodes"]} == {"domains_root"}


async def test_level2_nodes_sorted_by_label() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    r3 = await _ACTION.build_level2_nodes_aspect(None, BaseState(**r2), None, _duck(_FULL_GRAPH))  # type: ignore[arg-type]
    labels = [n.label.lower() for n in r3["level2_nodes"]]
    assert labels == sorted(labels)


# ─── Aspect 4: build_level3_diagrams_aspect ──────────────────────────────────


async def _run_to_level3(coordinator: dict) -> dict:
    conn = _duck(coordinator)
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    r3 = await _ACTION.build_level2_nodes_aspect(None, BaseState(**r2), None, conn)  # type: ignore[arg-type]
    return await _ACTION.build_level3_diagrams_aspect(None, BaseState(**r3), None, conn)  # type: ignore[arg-type]


async def test_level3_a_domain_with_nothing_has_no_rows() -> None:
    r = await _run_to_level3(_DOMAIN_ONLY)
    assert not [n for n in r["level3_diagrams"] if n.parent_id == "dom.billing"]


_DOMAIN_WITH_LIFECYCLE = {
    "nodes": [
        {"id": "dom.billing", "type": "Domain", "label": "Billing", "properties": {"name": "Billing", "description": ""}},
        {"id": "dom.empty", "type": "Domain", "label": "Empty", "properties": {"name": "Empty", "description": ""}},
        *_ENTITY_WITH_LIFECYCLE["nodes"],
    ],
    "edges": [
        *_ENTITY_WITH_LIFECYCLE["edges"],
        {"source_id": "ent.order", "target_id": "dom.billing", "type": "domain", "relationship": "Aggregation", "is_dag": False, "properties": {}},
    ],
}


async def test_level3_each_lifecycle_is_a_row_of_its_entitys_domain() -> None:
    r = await _run_to_level3(_DOMAIN_WITH_LIFECYCLE)
    rows = [n for n in r["level3_diagrams"] if n.type == "lifecycle_state_diagram"]
    assert [(n.id, n.parent_id, n.host_id, n.label, n.ordinal) for n in rows] == [("lc.status", "dom.billing", "ent.order", "Order lifecycle view", 2)]


async def test_level3_a_second_lifecycle_of_an_entity_is_named_by_its_field() -> None:
    coordinator = {
        "nodes": [*_DOMAIN_WITH_LIFECYCLE["nodes"], {"id": "lc.pay", "type": "Lifecycle", "label": "payment_state", "properties": {"field_name": "payment_state"}}],
        "edges": [
            *_DOMAIN_WITH_LIFECYCLE["edges"],
            {"source_id": "ent.order", "target_id": "lc.pay", "type": "lifecycle", "relationship": "Composition", "is_dag": False, "properties": {"field_name": "payment_state"}},
        ],
    }
    r = await _run_to_level3(coordinator)
    labels = sorted(n.label for n in r["level3_diagrams"] if n.type == "lifecycle_state_diagram")
    assert labels == ["Order order status view", "Order payment state view"]


async def test_level3_a_domain_with_entities_has_an_erd_and_no_use_case_row() -> None:
    r = await _run_to_level3(_DOMAIN_WITH_LIFECYCLE)
    assert {n.type for n in r["level3_diagrams"] if n.parent_id == "dom.billing"} == {"erd_domain", "lifecycle_state_diagram"}
    assert not [n for n in r["level3_diagrams"] if n.parent_id == "dom.empty"]


async def test_level3_a_domain_with_actions_has_a_use_case_and_no_erd_row() -> None:
    coordinator = {
        "nodes": [*_DOMAIN_ONLY["nodes"], {"id": "act.pay", "type": "Action", "label": "Pay", "properties": {"description": ""}}],
        "edges": [{"source_id": "act.pay", "target_id": "dom.billing", "type": "domain", "relationship": "Aggregation", "is_dag": False, "properties": {}}],
    }
    r = await _run_to_level3(coordinator)
    assert {n.type for n in r["level3_diagrams"] if n.parent_id == "dom.billing"} == {"use_case_domain"}


async def test_level3_holds_no_entity_rows() -> None:
    r = await _run_to_level3(_DOMAIN_WITH_LIFECYCLE)
    assert not [n for n in r["level3_diagrams"] if n.parent_id == "ent.order"]


# ─── Summary: build_result_summary ───────────────────────────────────────────


async def test_full_pipeline_result_layers() -> None:
    conn = _duck(_FULL_GRAPH)
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    r3 = await _ACTION.build_level2_nodes_aspect(None, BaseState(**r2), None, conn)  # type: ignore[arg-type]
    r4 = await _ACTION.build_level3_diagrams_aspect(None, BaseState(**r3), None, conn)  # type: ignore[arg-type]
    result = await _ACTION.build_result_summary(None, BaseState(**r4), None, conn)  # type: ignore[arg-type]

    assert isinstance(result, GetLeftMenuSidebarDataAction.Result)
    assert len(result.level1_nodes) == len(_ROOT_SECTIONS)
    assert len(result.level2_diagrams) == 3
    assert len(result.level2_nodes) == 2  # the 2 domains


async def test_full_pipeline_level3_types() -> None:
    conn = _duck(_FULL_GRAPH)
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    r3 = await _ACTION.build_level2_nodes_aspect(None, BaseState(**r2), None, conn)  # type: ignore[arg-type]
    r4 = await _ACTION.build_level3_diagrams_aspect(None, BaseState(**r3), None, conn)  # type: ignore[arg-type]
    result = await _ACTION.build_result_summary(None, BaseState(**r4), None, conn)  # type: ignore[arg-type]

    types = {n.type for n in result.level3_diagrams}
    assert "entity_class_diagram" not in types
    assert "lifecycle_state_diagram" not in types  # its entity stands in no domain here
