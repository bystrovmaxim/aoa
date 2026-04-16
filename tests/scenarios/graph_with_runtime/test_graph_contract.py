# tests/scenarios/graph_with_runtime/test_graph_contract.py
"""
Contract tests for the metadata graph and external JSON (MCP).

Lock in public API promises of ``GateCoordinator`` and ``_build_graph_json``:
if the contract changes, tests fail and require a deliberate update.

They do not duplicate all of ``test_graph_skeleton_and_hydrate`` — they add
field schema and a stable contract for consumers (agents, adapters).
"""

from __future__ import annotations

import json
import re
from typing import Any, Final

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.integrations.mcp.adapter import _build_graph_json
from action_machine.runtime.machines.core_action_machine import CoreActionMachine

# Register a minimal action in the BaseAction subclass tree before build().
from tests.scenarios.domain_model import PingAction

# --- Contract: raw node from facet ``get_graph()`` (no ``meta``) -----------------
GRAPH_NODE_SKELETON_KEYS: Final[frozenset[str]] = frozenset({
    "node_type",
    "name",
    "class_ref",
})

# --- Contract: hydrated node (API / hydrate_graph_node) -------------
HYDRATED_NODE_REQUIRED_KEYS: Final[frozenset[str]] = frozenset({
    "node_type",
    "name",
    "class_ref",
    "meta",
})

# --- Contract: MCP graph JSON root ---------------------------------------
MCP_GRAPH_TOP_KEYS: Final[frozenset[str]] = frozenset({"nodes", "edges"})

# --- Contract: edge in MCP JSON ----------------------------------------------
MCP_EDGE_KEYS: Final[frozenset[str]] = frozenset({
    "from",
    "to",
    "source_key",
    "target_key",
    "type",
})

# --- Contract: minimal node in MCP JSON ---------------------------------
MCP_NODE_MIN_KEYS: Final[frozenset[str]] = frozenset({"id", "type"})


def _default_coordinator() -> GateCoordinator:
    return CoreActionMachine.create_coordinator(logical_graph_public=False)


def test_contract_raw_graph_nodes_are_skeleton_only() -> None:
    """Every payload in ``get_graph()`` has exactly three keys, no ``meta``."""
    coord = _default_coordinator()
    graph = coord.get_graph()
    for idx in graph.node_indices():
        raw = dict(graph[idx])
        assert "meta" not in raw
        assert set(raw.keys()) == GRAPH_NODE_SKELETON_KEYS
        assert isinstance(raw["node_type"], str)
        assert isinstance(raw["name"], str)
        cr = raw["class_ref"]
        assert cr is None or isinstance(cr, type)


def test_contract_hydrate_always_adds_meta_dict() -> None:
    """``hydrate_graph_node`` always returns ``meta`` as a ``dict``."""
    coord = _default_coordinator()
    graph = coord.get_graph()
    for idx in graph.node_indices():
        raw = dict(graph[idx])
        hydrated = coord.hydrate_graph_node(raw)
        assert set(hydrated.keys()) >= HYDRATED_NODE_REQUIRED_KEYS
        assert isinstance(hydrated["meta"], dict)


def test_contract_get_node_shape_matches_hydrate() -> None:
    """``get_node`` returns the same field set as hydrating the raw node."""
    coord = _default_coordinator()
    nm = BaseIntentInspector._make_node_name(PingAction)
    node = coord.get_node("meta", nm)
    assert node is not None
    graph = coord.get_graph()
    idx = next(
        i
        for i in graph.node_indices()
        if graph[i]["node_type"] == "meta" and graph[i]["name"] == nm
    )
    assert node == coord.hydrate_graph_node(dict(graph[idx]))


def test_contract_ping_action_meta_snapshot_present() -> None:
    """For reference ``PingAction``, ``meta`` snapshot exists and is non-empty."""
    coord = _default_coordinator()
    snap = coord.get_snapshot(PingAction, "meta")
    assert snap is not None
    meta = dict(snap.to_facet_payload().node_meta)
    assert "description" in meta
    assert meta.get("domain") is not None


def test_contract_node_keys_follow_type_name_pattern() -> None:
    """Node key ``node_type:name`` matches payload fields."""
    coord = _default_coordinator()
    graph = coord.get_graph()
    for idx in graph.node_indices():
        p = graph[idx]
        nt, nm = p["node_type"], p["name"]
        expected_key = f"{nt}:{nm}"
        assert coord.get_node(expected_key) is not None


def test_contract_mcp_graph_json_schema() -> None:
    """JSON ``system://graph``: root, nodes, edges use fixed keys."""
    coord = _default_coordinator()
    data = json.loads(_build_graph_json(coord))
    assert set(data.keys()) == MCP_GRAPH_TOP_KEYS

    nodes = data["nodes"]
    edges = data["edges"]
    assert isinstance(nodes, list)
    assert isinstance(edges, list)
    assert nodes, "expected non-empty graph in contract fixture"

    node_key_re = re.compile(r"^[^:]+:.+$")
    seen_ids: set[str] = set()
    for n in nodes:
        assert isinstance(n, dict)
        assert set(n.keys()) >= MCP_NODE_MIN_KEYS, f"node missing keys: {n!r}"
        nid = n["id"]
        ntype = n["type"]
        assert isinstance(nid, str) and nid
        assert isinstance(ntype, str) and ntype
        seen_ids.add(f"{ntype}:{nid}")

    for e in edges:
        assert isinstance(e, dict)
        assert set(e.keys()) >= MCP_EDGE_KEYS, f"edge missing keys: {e!r}"
        sk = e["source_key"]
        tk = e["target_key"]
        assert isinstance(sk, str) and node_key_re.match(sk)
        assert isinstance(tk, str) and node_key_re.match(tk)
        assert sk in seen_ids, f"source_key not matching any node: {sk}"
        assert tk in seen_ids, f"target_key not matching any node: {tk}"
        assert isinstance(e["type"], str)


def test_contract_mcp_edge_keys_match_node_coordinates() -> None:
    """``source_key`` / ``target_key`` match ``type:id`` of MCP JSON nodes."""
    coord = _default_coordinator()
    data: dict[str, Any] = json.loads(_build_graph_json(coord))
    id_by_coord = {f"{n['type']}:{n['id']}": n for n in data["nodes"]}
    for e in data["edges"]:
        assert id_by_coord.get(e["source_key"]) is not None
        assert id_by_coord.get(e["target_key"]) is not None
