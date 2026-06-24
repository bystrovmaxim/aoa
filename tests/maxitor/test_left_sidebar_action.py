# tests/maxitor/test_left_sidebar_action.py
"""Tests for GetLeftMenuSidebarDataAction — one test group per aspect."""

from __future__ import annotations

from aoa.action_machine.model import BaseState
from aoa.maxitor.model.core.actions.left_sidebar_action import (
    _ROOT_SECTIONS,
    GetLeftMenuSidebarDataAction,
)
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

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
        {"id": "ent.order", "type": "Entity", "label": "Order", "properties": {"description": ""}},
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
        {"id": "ent.order", "type": "Entity", "label": "Order", "properties": {"description": ""}},
        {"id": "ent.invoice", "type": "Entity", "label": "Invoice", "properties": {"description": ""}},
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
    assert len(r2["level2_diagrams"]) == 2


async def test_level2_diagrams_ids() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    ids = {n.id for n in r2["level2_diagrams"]}
    assert ids == {"application_interchange_graph", "domains_all_erd"}


async def test_level2_diagrams_labels_have_view_suffix() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    for n in r2["level2_diagrams"]:
        assert n.label.endswith(" view"), n.label


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


async def test_level2_nodes_entity_goes_to_entities_root() -> None:
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    r3 = await _ACTION.build_level2_nodes_aspect(None, BaseState(**r2), None, _duck(_ENTITY_WITH_LIFECYCLE))  # type: ignore[arg-type]
    entity_node = next(n for n in r3["level2_nodes"] if n.id == "ent.order")
    assert entity_node.parent_id == "entities_root"
    assert entity_node.type == "Entity"


async def test_level2_nodes_unknown_type_falls_back_to_last_root() -> None:
    # Lifecycle has no dedicated root section → falls back to resources_root (last).
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    r3 = await _ACTION.build_level2_nodes_aspect(None, BaseState(**r2), None, _duck(_ENTITY_WITH_LIFECYCLE))  # type: ignore[arg-type]
    lc_node = next(n for n in r3["level2_nodes"] if n.id == "lc.status")
    assert lc_node.parent_id == "resources_root"


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


async def test_level3_domain_creates_erd_and_use_case_rows() -> None:
    r = await _run_to_level3(_DOMAIN_ONLY)
    types = {n.type for n in r["level3_diagrams"] if n.parent_id == "dom.billing"}
    assert types == {"erd_domain", "use_case_domain"}


async def test_level3_domain_row_ids() -> None:
    r = await _run_to_level3(_DOMAIN_ONLY)
    ids = {n.id for n in r["level3_diagrams"]}
    assert "erd_domain:dom.billing" in ids
    assert "use_case_domain:dom.billing" in ids


async def test_level3_entity_without_lifecycle_has_one_row() -> None:
    coordinator = {
        "nodes": [{"id": "ent.invoice", "type": "Entity", "label": "Invoice", "properties": {"description": ""}}],
        "edges": [],
    }
    r = await _run_to_level3(coordinator)
    entity_rows = [n for n in r["level3_diagrams"] if n.parent_id == "ent.invoice"]
    assert len(entity_rows) == 1
    assert entity_rows[0].type == "entity_class_diagram"
    assert entity_rows[0].ordinal == 0


async def test_level3_entity_with_lifecycle_has_lifecycle_row() -> None:
    r = await _run_to_level3(_ENTITY_WITH_LIFECYCLE)
    entity_rows = [n for n in r["level3_diagrams"] if n.parent_id == "ent.order"]
    types = {n.type for n in entity_rows}
    assert "entity_class_diagram" in types
    assert "lifecycle_state_diagram" in types
    lc_row = next(n for n in entity_rows if n.type == "lifecycle_state_diagram")
    assert lc_row.id == "lc.status"
    assert lc_row.ordinal == 1


async def test_level3_ordinals_entity_before_lifecycle() -> None:
    r = await _run_to_level3(_ENTITY_WITH_LIFECYCLE)
    rows = sorted(
        [n for n in r["level3_diagrams"] if n.parent_id == "ent.order"],
        key=lambda n: n.ordinal or 0,
    )
    assert rows[0].type == "entity_class_diagram"
    assert rows[1].type == "lifecycle_state_diagram"


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
    assert len(result.level2_diagrams) == 2
    assert len(result.level2_nodes) == 5  # 2 domains + 2 entities + 1 lifecycle


async def test_full_pipeline_level3_types() -> None:
    conn = _duck(_FULL_GRAPH)
    r1 = await _ACTION.build_level1_aspect(None, BaseState(), None, {})  # type: ignore[arg-type]
    r2 = await _ACTION.build_level2_diagrams_aspect(None, BaseState(**r1), None, {})  # type: ignore[arg-type]
    r3 = await _ACTION.build_level2_nodes_aspect(None, BaseState(**r2), None, conn)  # type: ignore[arg-type]
    r4 = await _ACTION.build_level3_diagrams_aspect(None, BaseState(**r3), None, conn)  # type: ignore[arg-type]
    result = await _ACTION.build_result_summary(None, BaseState(**r4), None, conn)  # type: ignore[arg-type]

    types = {n.type for n in result.level3_diagrams}
    assert "erd_domain" in types
    assert "use_case_domain" in types
    assert "entity_class_diagram" in types
    assert "lifecycle_state_diagram" in types
