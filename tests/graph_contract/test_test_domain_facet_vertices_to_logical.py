# tests/graph_contract/test_test_domain_facet_vertices_to_logical.py

"""
Collect real ``FacetVertex`` rows from ``maxitor.samples`` (unbuilt coordinator) and feed
:mod:`action_machine.graph.graph_builder`; snapshot smoke on built coordinator (A2-style).
"""

from __future__ import annotations

import importlib

import pytest

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.graph_builder import build_interchange_from_facet_vertices
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from maxitor.samples.build import _MODULES, build_sample_coordinator
from maxitor.samples.store.actions.checkout_submit import CheckoutSubmitAction
from maxitor.samples.store.domain import StoreDomain

from .facet_vertex_probe import (
    collect_merged_facet_vertices_unbuilt,
    graph_coordinator_default_inspectors_registered,
)


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_collect_raises_when_coordinator_already_built() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator()
    with pytest.raises(RuntimeError, match="before build"):
        collect_merged_facet_vertices_unbuilt(coord)


def test_build_interchange_from_test_domain_payloads() -> None:
    _import_test_domain_modules()
    coord = graph_coordinator_default_inspectors_registered()
    payloads = collect_merged_facet_vertices_unbuilt(coord)
    vertices, edges = build_interchange_from_facet_vertices(payloads)

    vertex_ids = {v.id for v in vertices}
    for e in edges:
        assert e.source_id in vertex_ids, e
        assert e.target_id in vertex_ids, e

    action_id = BaseIntentInspector._make_node_name(CheckoutSubmitAction)
    domain_id = BaseIntentInspector._make_node_name(StoreDomain)
    assert action_id in vertex_ids
    assert domain_id in vertex_ids

    coord.build()
    assert coord._built is True


def test_built_coordinator_meta_snapshot_for_full_graph_action() -> None:
    """A2-style: known action still exposes meta snapshot after full build."""
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    snap = coord.get_snapshot(CheckoutSubmitAction, "meta")
    assert snap is not None


def test_interchange_output_vertex_ids_unique() -> None:
    _import_test_domain_modules()
    coord = graph_coordinator_default_inspectors_registered()
    raw = collect_merged_facet_vertices_unbuilt(coord)
    vertices, _edges = build_interchange_from_facet_vertices(raw)
    ids = [v.id for v in vertices]
    assert len(ids) == len(set(ids))


def test_create_coordinator_factory_still_builds_non_trivial_graph() -> None:
    """Regression: default factory path used by runtime remains healthy after refactor."""
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator()
    assert len(coord.get_graph()) >= 5


def test_built_coordinator_role_snapshot_for_full_graph_action() -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    assert coord.get_snapshot(CheckoutSubmitAction, "role") is not None
