# tests/graph_logical_contract/test_pr4_gate_coordinator_logical_graph.py

"""PR4: ``GateCoordinator.get_logical_graph()`` alongside facet and public ``get_graph()``."""

from __future__ import annotations

import importlib

import pytest
import rustworkx as rx

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.logical import LogicalGraphBuilder, narrow_facet_payloads_for_logical_build
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from maxitor.test_domain.actions.full_graph import TestFullGraphAction
from maxitor.test_domain.build import _MODULES, build_test_coordinator
from maxitor.test_domain.domain import TestDomain

from .facet_payload_probe import collect_merged_facet_payloads_unbuilt


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_pr4_get_logical_graph_requires_build() -> None:
    gc = CoreActionMachine.create_coordinator_unbuilt()
    with pytest.raises(RuntimeError, match="not built"):
        gc.get_logical_graph()


def test_pr4_logical_graph_matches_standalone_builder_on_test_domain() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator()
    lg = coord.get_logical_graph()
    assert isinstance(lg, rx.PyDiGraph)
    assert len(lg) >= 1

    unbuilt = CoreActionMachine.create_coordinator_unbuilt()
    payloads = collect_merged_facet_payloads_unbuilt(unbuilt)
    narrow = narrow_facet_payloads_for_logical_build(payloads)
    vertices, edges = LogicalGraphBuilder.build(facet_payloads=narrow)
    assert len(lg) == len(vertices)
    assert len(lg.weighted_edge_list()) == len(edges)


def test_pr4_logical_node_payload_shape() -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    lg = coord.get_logical_graph()
    for idx in lg.node_indices():
        data = lg[idx]
        assert set(data.keys()) >= {
            "vertex_type",
            "id",
            "stereotype",
            "display_name",
            "class_ref",
            "properties",
        }


def test_pr4_facet_graph_counters_match_get_graph_logical_is_narrower_nodes() -> None:
    """Facet skeleton (``get_facet_graph``) is at least as large as the logical slice.

    Default ``get_graph()`` is logical; facet topology is read via ``get_facet_graph``.
    Logical interchange may emit **more** edges than the facet graph (expanded
    projection), so there is no ordering invariant between edge counts.
    """
    _import_test_domain_modules()
    coord = build_test_coordinator()
    logical_nodes = len(coord.get_graph())
    logical_edges = len(coord.get_graph().weighted_edge_list())
    assert coord.graph_node_count == logical_nodes
    assert coord.graph_edge_count == logical_edges
    assert logical_nodes == len(coord.get_logical_graph())
    with pytest.warns(DeprecationWarning, match="get_facet_graph"):
        facet_g = coord.get_facet_graph()
    facet_nodes = len(facet_g)
    assert facet_nodes >= logical_nodes
    assert logical_nodes >= 1


def test_pr4_known_action_and_domain_present_in_logical_graph() -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    lg = coord.get_logical_graph()
    ids = {lg[idx]["id"] for idx in lg.node_indices()}
    assert BaseIntentInspector._make_node_name(TestFullGraphAction) in ids
    assert BaseIntentInspector._make_node_name(TestDomain) in ids
