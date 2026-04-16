# tests/graph_logical_contract/test_coordinator_logical_facet_invariants.py

"""Invariants across logical ``get_graph``, ``get_logical_graph``, ``facet_topology_copy``, MCP, and hydration."""

from __future__ import annotations

import importlib
import warnings

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.graph.payload import FacetPayload
from action_machine.integrations.mcp.adapter import _build_graph_json
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from maxitor.test_domain.actions.full_graph import TestFullGraphAction
from maxitor.test_domain.build import _MODULES, build_test_coordinator


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_get_graph_matches_get_logical_graph_payloads_test_domain() -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    g = coord.get_graph()
    lg = coord.get_logical_graph()
    assert g.num_nodes() == lg.num_nodes()
    assert g.num_edges() == lg.num_edges()
    for idx in g.node_indices():
        assert g[idx] == lg[idx]


def test_facet_topology_copy_returns_distinct_equal_clones() -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    a = coord.facet_topology_copy()
    b = coord.facet_topology_copy()
    assert a is not b
    assert a.num_nodes() == b.num_nodes()
    for idx in a.node_indices():
        assert dict(a[idx]) == dict(b[idx])


def test_hydrate_facet_raw_payload_matches_get_node_for_meta_node() -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    nm = BaseIntentInspector._make_node_name(TestFullGraphAction)
    facet = coord.facet_topology_copy()
    idx = next(
        i
        for i in facet.node_indices()
        if facet[i].get("node_type") == "meta" and facet[i].get("name") == nm
    )
    raw = dict(facet[idx])
    assert coord.get_node("meta", nm) == coord.hydrate_graph_node(raw)


def test_hydrate_logical_graph_payload_does_not_fill_facet_meta() -> None:
    """Passing a logical interchange dict is unsupported; ``meta`` stays empty and ``node_type`` is absent."""
    _import_test_domain_modules()
    coord = build_test_coordinator()
    g = coord.get_graph()
    idx = next(iter(g.node_indices()))
    raw = dict(g[idx])
    assert "vertex_type" in raw
    hydrated = coord.hydrate_graph_node(raw)
    assert hydrated.get("meta") == {}
    assert "node_type" not in hydrated


def test_mcp_build_graph_json_emits_no_deprecation_warnings() -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        _build_graph_json(coord)
    assert not any(issubclass(r.category, DeprecationWarning) for r in rec)


def test_create_coordinator_unbuilt_then_build_matches_default_factory_graph() -> None:
    _import_test_domain_modules()
    a = CoreActionMachine.create_coordinator()
    b = CoreActionMachine.create_coordinator_unbuilt().build()
    assert a.graph_node_count == b.graph_node_count
    assert a.graph_edge_count == b.graph_edge_count
    assert len(a.get_graph()) == len(b.get_graph())


def test_gate_coordinator_has_no_get_facet_graph() -> None:
    assert not hasattr(GateCoordinator, "get_facet_graph")


class _OrphanFacetClass:
    pass


class _OrphanFacetInspector(BaseIntentInspector):
    """Emits a facet node type outside the narrow logical projection (empty logical graph)."""

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return [_OrphanFacetClass]

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        return FacetPayload(node_type="orphan_kind", node_name="n", node_class=target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        raise NotImplementedError


def test_facet_nonempty_logical_empty_when_facet_kind_not_in_logical_projection() -> None:
    coord = GateCoordinator().register(_OrphanFacetInspector).build()
    assert len(coord.facet_topology_copy()) == 1
    assert coord.graph_node_count == 0
    assert len(coord.get_graph()) == 0
    assert coord.get_node("orphan_kind", "n") is not None
