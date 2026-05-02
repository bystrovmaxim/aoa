# tests/graph_contract/test_graph_public_opt_in.py

"""Public interchange ``get_graph()`` vs internal facet skeleton ``facet_topology_copy()``."""

from __future__ import annotations

import importlib
import json

import pytest

from action_machine.integrations.mcp.adapter import _build_graph_json
from action_machine.legacy.core import Core
from graph.create_node_graph_coordinator import create_node_graph_coordinator
from maxitor.samples.build import _MODULES


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_default_get_graph_returns_interchange() -> None:
    _import_test_domain_modules()
    coord = Core.create_coordinator()
    g = coord.get_graph()
    assert "node_type" in g[0]
    assert len(g) == len(coord.get_graph())


def test_default_graph_counts_match_get_graph() -> None:
    _import_test_domain_modules()
    coord = Core.create_coordinator()
    assert coord.graph_node_count == len(coord.get_graph())
    assert coord.graph_edge_count == len(coord.get_graph().weighted_edge_list())


def test_mcp_build_graph_json_uses_node_graph_shape() -> None:
    _import_test_domain_modules()
    coord = create_node_graph_coordinator()
    raw = _build_graph_json(coord)
    data = json.loads(raw)
    assert data["nodes"]
    for node in data["nodes"]:
        assert "type" in node


@pytest.mark.facet_skeleton
def test_facet_topology_copy_matches_facet_get_graph_shape() -> None:
    coord = Core.create_coordinator()
    facet = coord.facet_topology_copy()
    assert "node_type" in facet[0]
    assert len(facet) >= len(coord.get_graph())
