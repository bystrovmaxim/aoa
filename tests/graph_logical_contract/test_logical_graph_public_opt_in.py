# tests/graph_logical_contract/test_logical_graph_public_opt_in.py

"""Default logical ``get_graph()`` and opt-out facet skeleton on ``GateCoordinator``."""

from __future__ import annotations

import importlib
import json
import warnings

import pytest

from action_machine.integrations.mcp.adapter import _build_graph_json
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from maxitor.test_domain.build import _MODULES


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_default_get_graph_returns_logical_interchange() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator()
    g = coord.get_graph()
    assert "vertex_type" in g[0]
    assert len(g) == len(coord.get_logical_graph())


def test_default_graph_counts_match_logical_get_graph() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator()
    assert coord.graph_node_count == len(coord.get_graph())
    assert coord.graph_edge_count == len(coord.get_graph().weighted_edge_list())


def test_mcp_build_graph_json_stays_facet_shaped_with_default_logical_public() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator()
    raw = _build_graph_json(coord)
    data = json.loads(raw)
    assert data["nodes"]
    for node in data["nodes"]:
        assert "type" in node


@pytest.mark.facet_skeleton
def test_get_facet_graph_emits_deprecation_warning() -> None:
    _import_test_domain_modules()
    coord = CoreActionMachine.create_coordinator()
    with pytest.warns(DeprecationWarning, match="get_facet_graph"):
        coord.get_facet_graph()


@pytest.mark.facet_skeleton
def test_logical_graph_public_false_get_graph_remains_facet_skeleton() -> None:
    coord = CoreActionMachine.create_coordinator(logical_graph_public=False)
    g = coord.get_graph()
    assert "node_type" in g[0]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        facet = coord.get_facet_graph()
    assert len(facet) == len(g)
