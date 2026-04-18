# tests/scenarios/graph_with_runtime/test_graph_skeleton_and_hydrate.py
"""
Tests: ``rx.PyDiGraph`` nodes are skeleton-only; ``meta`` comes from snapshots and ``hydrate_graph_node``.
"""

from __future__ import annotations

import pytest

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.interchange_vertex_labels import DEPENDENCY_SERVICE_VERTEX_TYPE
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from tests.scenarios.domain_model import CompensatedOrderAction, FullAction, TestDbManager
from tests.scenarios.domain_model.domains import OrdersDomain
from tests.scenarios.domain_model.services import PaymentService


def test_get_graph_node_payloads_are_skeleton_only() -> None:
    """Each node payload in the graph copy has exactly three keys, no ``meta``."""
    coord = CoreActionMachine.create_coordinator()
    g = coord.facet_topology_copy()
    for idx in g.node_indices():
        raw = dict(g[idx])
        assert "meta" not in raw
        keys = set(raw.keys())
        assert {"node_type", "id", "class_ref"} <= keys
        assert keys <= {"node_type", "id", "class_ref", "committed_meta"}


def test_hydrate_graph_node_restores_meta_from_snapshot() -> None:
    """``hydrate_graph_node`` matches ``get_node`` for a ``resource_manager`` @meta host."""
    coord = CoreActionMachine.create_coordinator()
    rm_nm = BaseIntentInspector._make_node_name(TestDbManager)
    g = coord.facet_topology_copy()
    idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "resource_manager" and g[i]["id"] == rm_nm
    )
    raw = dict(g[idx])
    hydrated = coord.hydrate_graph_node(raw)
    via_api = coord.get_node("resource_manager", rm_nm)
    assert via_api is not None
    assert hydrated["meta"] == via_api["meta"]
    assert hydrated["meta"]
    assert "description" in hydrated["meta"]
    assert "domain" not in hydrated["meta"]


def test_hydrated_action_node_merges_meta_from_snapshots() -> None:
    """Merged ``action`` host hydrates ``meta`` from every snapshot key (e.g. ``@meta`` + ``depends``)."""
    coord = CoreActionMachine.create_coordinator()
    g = coord.facet_topology_copy()
    action_indices = [
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "action" and g[i]["class_ref"] is FullAction
    ]
    assert action_indices, "expected FullAction structural action node"
    raw = dict(g[action_indices[0]])
    meta = coord.hydrate_graph_node(raw).get("meta") or {}
    assert "description" in meta


def test_hydrate_graph_node_requires_build() -> None:
    """Hydration is forbidden before ``build()``."""
    c = GraphCoordinator()
    with pytest.raises(RuntimeError, match="not built"):
        c.hydrate_graph_node({
            "node_type": "meta",
            "id": "x",
            "class_ref": object,
        })


def test_get_nodes_by_type_includes_hydrated_meta() -> None:
    """``get_nodes_by_type`` returns records with non-empty ``meta`` when a snapshot exists."""
    coord = CoreActionMachine.create_coordinator()
    rm_nm = BaseIntentInspector._make_node_name(TestDbManager)
    rm_nodes = [
        n for n in coord.get_nodes_by_type("resource_manager") if n["id"] == rm_nm
    ]
    assert len(rm_nodes) == 1
    assert rm_nodes[0].get("meta")


def test_stub_dependency_node_hydrates_to_empty_meta() -> None:
    """Stub dependency nodes (no snapshot) yield empty ``meta``."""
    coord = CoreActionMachine.create_coordinator()
    dep_nodes = [
        n
        for n in coord.get_nodes_for_class(PaymentService)
        if n.get("class_ref") is PaymentService
    ]
    assert dep_nodes, "expected PaymentService dependency stub in default graph"
    assert dep_nodes[0].get("meta") == {}

    g = coord.facet_topology_copy()
    idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == DEPENDENCY_SERVICE_VERTEX_TYPE
        and g[i]["class_ref"] is PaymentService
    )
    assert coord.hydrate_graph_node(dict(g[idx])).get("meta") == {}


def test_hydration_mapping_from_build_records_meta_snapshot_key() -> None:
    """Phase 1 records snapshot key ``meta`` for ``resource_manager`` graph nodes."""
    coord = CoreActionMachine.create_coordinator()
    rm_nm = BaseIntentInspector._make_node_name(TestDbManager)
    gk_rm = GraphCoordinator._make_key("resource_manager", rm_nm)
    raw_map = coord._hydration_snapshot_key_by_graph_key
    assert raw_map.get(gk_rm) == "meta"


def test_merged_action_node_records_all_hydration_keys() -> None:
    """Merged ``action`` with @depends, @connection, and @meta lists every snapshot storage key."""
    coord = CoreActionMachine.create_coordinator()
    nm = BaseIntentInspector._make_node_name(FullAction)
    gk_action = f"action:{nm}"
    raw_map = coord._hydration_snapshot_key_by_graph_key
    assert raw_map[gk_action] == (
        "action_schemas",
        "connections",
        "depends",
        "meta",
        "role",
    )


def test_connection_targets_resource_manager_not_connection_facet() -> None:
    """``@connection`` adds edges from ``action`` to ``resource_manager`` (no ``connection`` facet node)."""
    coord = CoreActionMachine.create_coordinator()
    rm_nm = BaseIntentInspector._make_node_name(TestDbManager)
    assert [n for n in coord.get_nodes_by_type("resource_manager") if n["id"] == rm_nm]
    assert not [
        n
        for n in coord.get_nodes_by_type("connection")
        if n.get("class_ref") is TestDbManager
    ]

    act_nm = BaseIntentInspector._make_node_name(FullAction)
    g = coord.facet_topology_copy()
    action_idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "action" and g[i]["id"] == act_nm
    )
    connection_targets: list[str] = []
    for _s, t, ep in g.out_edges(action_idx):
        if isinstance(ep, dict) and ep.get("edge_type") == "connection":
            connection_targets.append(g[t]["id"])
    assert rm_nm in connection_targets


def test_stub_domain_node_hydrates_with_domain_snapshot_meta() -> None:
    """``domain`` node for ``OrdersDomain`` picks up class-level ``@meta`` snapshot."""
    coord = CoreActionMachine.create_coordinator()
    dom_nodes = [
        n
        for n in coord.get_nodes_by_type("domain")
        if n.get("class_ref") is OrdersDomain
    ]
    assert dom_nodes, "expected OrdersDomain node from @meta(domain=...)"
    meta = dom_nodes[0].get("meta") or {}
    assert meta.get("name") == "orders"

    g = coord.facet_topology_copy()
    idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "domain" and g[i]["class_ref"] is OrdersDomain
    )
    hydrated_meta = coord.hydrate_graph_node(dict(g[idx])).get("meta") or {}
    assert hydrated_meta.get("name") == "orders"


def test_action_depends_and_meta_merge_hydration_keys() -> None:
    """
    @depends with @meta on the same action: two snapshot keys, merged ``meta`` on hydrate.
    """
    coord = CoreActionMachine.create_coordinator()
    nm = BaseIntentInspector._make_node_name(CompensatedOrderAction)
    gk = f"action:{nm}"
    raw_map = coord._hydration_snapshot_key_by_graph_key
    assert set(raw_map.get(gk)) == {
        "action_schemas",
        "compensator",
        "depends",
        "meta",
        "role",
    }

    g = coord.facet_topology_copy()
    idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "action" and g[i]["class_ref"] is CompensatedOrderAction
    )
    meta = coord.hydrate_graph_node(dict(g[idx])).get("meta") or {}
    assert "description" in meta
