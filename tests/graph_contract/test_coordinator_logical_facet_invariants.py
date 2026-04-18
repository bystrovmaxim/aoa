# tests/graph_contract/test_coordinator_logical_facet_invariants.py

"""Invariants across ``get_graph``, ``facet_topology_copy``, MCP, and hydration."""

from __future__ import annotations

import importlib
import warnings

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.facet_payload import FacetPayload
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.integrations.mcp.adapter import _build_graph_json
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from maxitor.samples.build import _MODULES, build_sample_coordinator
from maxitor.samples.store.actions.checkout_submit import CheckoutSubmitAction

from .facet_payload_probe import graph_coordinator_default_inspectors_registered


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_get_graph_clones_equal_payloads_test_domain() -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    a = coord.get_graph()
    b = coord.get_graph()
    assert a.num_nodes() == b.num_nodes()
    assert a.num_edges() == b.num_edges()
    for idx in a.node_indices():
        assert a[idx] == b[idx]


def test_facet_topology_copy_returns_distinct_equal_clones() -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    a = coord.facet_topology_copy()
    b = coord.facet_topology_copy()
    assert a is not b
    assert a.num_nodes() == b.num_nodes()
    for idx in a.node_indices():
        assert dict(a[idx]) == dict(b[idx])


def test_hydrate_facet_raw_payload_matches_get_node_for_merged_action_host() -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    nm = BaseIntentInspector._make_node_name(CheckoutSubmitAction)
    facet = coord.facet_topology_copy()
    idx = next(
        i
        for i in facet.node_indices()
        if facet[i].get("node_type") == "Action" and facet[i].get("id") == nm
    )
    raw = dict(facet[idx])
    assert coord.get_node("Action", nm) == coord.hydrate_graph_node(raw)


def test_hydrate_logical_graph_payload_does_not_fill_facet_rows() -> None:
    """Interchange payloads may be passed to ``hydrate_graph_node``; ``node_type`` is preserved, ``facet_rows`` may stay empty."""
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    g = coord.get_graph()
    idx = next(iter(g.node_indices()))
    raw = dict(g[idx])
    assert "node_type" in raw
    hydrated = coord.hydrate_graph_node(raw)
    assert hydrated.get("facet_rows") == {}
    assert hydrated.get("node_type") == raw.get("node_type")


def test_mcp_build_graph_json_emits_no_deprecation_warnings() -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        _build_graph_json(coord)
    assert not any(issubclass(r.category, DeprecationWarning) for r in rec)


def test_manual_register_then_build_matches_create_coordinator() -> None:
    _import_test_domain_modules()
    a = CoreActionMachine.create_coordinator()
    b = graph_coordinator_default_inspectors_registered().build()
    assert a.graph_node_count == b.graph_node_count
    assert a.graph_edge_count == b.graph_edge_count
    assert len(a.get_graph()) == len(b.get_graph())


def test_gate_coordinator_has_no_get_facet_graph() -> None:
    assert not hasattr(GraphCoordinator, "get_facet_graph")


class _OrphanFacetClass:
    pass


class _OrphanFacetInspector(BaseIntentInspector):
    """Emits a facet node type with no special-case edges (generic interchange vertex only)."""

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return [_OrphanFacetClass]

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        return FacetPayload(node_type="orphan_kind", node_name="n", node_class=target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        raise NotImplementedError


def test_facet_nonempty_and_interchange_includes_orphan_kind_vertex() -> None:
    coord = GraphCoordinator().register(_OrphanFacetInspector).build()
    assert len(coord.facet_topology_copy()) == 1
    assert coord.graph_node_count == 1
    assert len(coord.get_graph()) == 1
    assert coord.get_node("orphan_kind", "n") is not None
