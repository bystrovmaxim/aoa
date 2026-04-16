# tests/graph_logical_contract/test_pr3_test_domain_facet_to_logical.py

"""
PR3: collect real ``FacetPayload`` rows from test_domain (unbuilt coordinator) and feed
``LogicalGraphBuilder``; snapshot smoke on built coordinator (A2-style).
"""

from __future__ import annotations

import importlib

import pytest

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.logical import (
    FACET_NODE_TYPES_FOR_LOGICAL_BUILD,
    LogicalGraphBuilder,
    narrow_facet_payloads_for_logical_build,
)
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from maxitor.test_domain.actions.full_graph import TestFullGraphAction
from maxitor.test_domain.build import _MODULES, build_test_coordinator
from maxitor.test_domain.domain import TestDomain

from .facet_payload_probe import collect_merged_facet_payloads_unbuilt


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_pr3_collect_raises_when_coordinator_already_built() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator()
    with pytest.raises(RuntimeError, match="before build"):
        collect_merged_facet_payloads_unbuilt(coord)


def test_pr3_narrow_logical_graph_from_test_domain_payloads() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator_unbuilt()
    payloads = collect_merged_facet_payloads_unbuilt(coord)
    narrow = narrow_facet_payloads_for_logical_build(payloads)
    vertices, edges = LogicalGraphBuilder.build(facet_payloads=narrow)

    vertex_ids = {v.id for v in vertices}
    for e in edges:
        assert e.source_id in vertex_ids, e
        assert e.target_id in vertex_ids, e

    action_id = BaseIntentInspector._make_node_name(TestFullGraphAction)
    domain_id = BaseIntentInspector._make_node_name(TestDomain)
    assert action_id in vertex_ids
    assert domain_id in vertex_ids

    coord.build()
    assert coord._built is True


def test_pr3_built_coordinator_meta_snapshot_for_full_graph_action() -> None:
    """A2-style: known action still exposes meta snapshot after full build."""
    _import_test_domain_modules()
    coord = build_test_coordinator()
    snap = coord.get_snapshot(TestFullGraphAction, "meta")
    assert snap is not None


def test_pr3_narrow_payloads_are_subset_of_raw_and_drop_rich_facets() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator_unbuilt()
    raw = collect_merged_facet_payloads_unbuilt(coord)
    narrow = narrow_facet_payloads_for_logical_build(raw)
    raw_set = set(raw)
    assert all(p in raw_set for p in narrow)
    raw_types = {p.node_type for p in raw}
    assert raw_types - FACET_NODE_TYPES_FOR_LOGICAL_BUILD, (
        "test_domain should emit facets outside PR2 narrow builder"
    )
    assert {p.node_type for p in narrow} <= FACET_NODE_TYPES_FOR_LOGICAL_BUILD


def test_pr3_logical_output_vertex_ids_unique() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator_unbuilt()
    raw = collect_merged_facet_payloads_unbuilt(coord)
    narrow = narrow_facet_payloads_for_logical_build(raw)
    vertices, _edges = LogicalGraphBuilder.build(facet_payloads=narrow)
    ids = [v.id for v in vertices]
    assert len(ids) == len(set(ids))


def test_pr3_create_coordinator_factory_still_builds_non_trivial_graph() -> None:
    """Regression: default factory path used by runtime remains healthy after refactor."""
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator()
    assert len(coord.get_graph()) >= 5


def test_pr3_built_coordinator_role_snapshot_for_full_graph_action() -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    assert coord.get_snapshot(TestFullGraphAction, "role") is not None
