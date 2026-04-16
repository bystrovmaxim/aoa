# tests/graph_logical_contract/test_logical_vertex_types_present.py

"""
PR5 matrix (plan 009): logical ``vertex_type`` values from test_domain narrow graph.

Full ``VERTEX_TYPES`` coverage with stubs or skips is PR11; here we lock the
subset produced by ``build_test_coordinator()`` today.
"""

from __future__ import annotations

import importlib

import pytest

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.logical import VERTEX_TYPES
from maxitor.test_domain.actions.full_graph import TestFullGraphAction
from maxitor.test_domain.build import _MODULES, build_test_coordinator
from maxitor.test_domain.domain import TestDomain

# Narrow facet logical projection (PR2–PR4) currently emits only these vertex kinds.
_TEST_DOMAIN_LOGICAL_VERTEX_TYPES: frozenset[str] = frozenset({"action", "domain", "role"})


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


@pytest.mark.graph_coverage
def test_logical_vertex_types_matrix_test_domain_narrow_projection() -> None:
    _import_test_domain_modules()
    lg = build_test_coordinator().get_logical_graph()
    present = {lg[idx]["vertex_type"] for idx in lg.node_indices()}
    assert present >= _TEST_DOMAIN_LOGICAL_VERTEX_TYPES
    assert present <= VERTEX_TYPES


@pytest.mark.graph_coverage
def test_c2_single_action_vertex_for_full_graph_action() -> None:
    """One logical ``action`` vertex per qualname (TestFullGraphAction)."""
    _import_test_domain_modules()
    lg = build_test_coordinator().get_logical_graph()
    action_id = BaseIntentInspector._make_node_name(TestFullGraphAction)
    matches = [lg[i] for i in lg.node_indices() if lg[i]["id"] == action_id]
    assert len(matches) == 1
    assert matches[0]["vertex_type"] == "action"


@pytest.mark.graph_coverage
def test_c2_single_domain_vertex_for_test_domain() -> None:
    _import_test_domain_modules()
    lg = build_test_coordinator().get_logical_graph()
    domain_id = BaseIntentInspector._make_node_name(TestDomain)
    matches = [lg[i] for i in lg.node_indices() if lg[i]["id"] == domain_id]
    assert len(matches) == 1
    assert matches[0]["vertex_type"] == "domain"
