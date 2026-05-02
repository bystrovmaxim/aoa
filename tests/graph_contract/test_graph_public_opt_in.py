# tests/graph_contract/test_graph_public_opt_in.py

"""Smoke: MCP JSON export uses the interchange node-graph shape."""

from __future__ import annotations

import importlib
import json

from action_machine.integrations.mcp.adapter import _build_graph_json
from graph.create_node_graph_coordinator import create_node_graph_coordinator
from maxitor.samples.build import _MODULES


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_mcp_build_graph_json_uses_node_graph_shape() -> None:
    _import_test_domain_modules()
    coord = create_node_graph_coordinator()
    raw = _build_graph_json(coord)
    data = json.loads(raw)
    assert data["nodes"]
    for node in data["nodes"]:
        assert "type" in node
