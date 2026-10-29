# packages/maxitor/front/src/maxitor/front/model/core/same_graph.py
"""
same_graph — whether two graph-json documents hold the same graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When the running service's graph is the newest version's graph, Live and that
version are one state, and the track shows one point for both. The two come from
different writers — the service answers its graph, the repository holds the file
graph-builder wrote — so their bytes may differ in order and spacing, and a
service wraps its graph as ``{"coordinator_json": "<the graph as a string>"}``,
while the graph is the same. They are compared as graphs: the same nodes and the
same edges, in any order.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

two bodies ──► parsed ──► nodes and edges, each written canonically, sorted ──► equal or not.
"""

from __future__ import annotations

import json
from typing import Any


def same_graph(first: bytes, second: bytes) -> bool:
    """
    AI-CORE-BEGIN
    ROLE: Tell whether two graph-json bodies hold the same graph.
    CONTRACT: True when both parse — a service's ``coordinator_json`` wrapper unwrapped — and have the same nodes and the same edges, whatever their order, key order or spacing; false otherwise, a body that is not a graph included. Never raises.
    AI-CORE-END
    """
    return _canonical(first) is not None and _canonical(first) == _canonical(second)


def _canonical(body: bytes) -> tuple[list[str], list[str]] | None:
    """A graph's nodes and edges, each written with sorted keys, sorted; ``None`` for a body that is not a graph."""
    try:
        document: Any = json.loads(body)
        if isinstance(document.get("coordinator_json"), str):
            document = json.loads(document["coordinator_json"])
        nodes, edges = document["nodes"], document["edges"]
        return sorted(json.dumps(node, sort_keys=True) for node in nodes), sorted(json.dumps(edge, sort_keys=True) for edge in edges)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None
