# packages/maxitor/core/graph_compare/tests/test_graph_compare_speed.py
"""Two versions of the demo's graph (3 213 nodes, 4 841 edges) compare in well under a second, and every edit is counted."""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any

from maxitor.graph_compare import Counts, Status, changed_inside, compare

DEMO_GRAPH = Path(__file__).resolve().parents[5] / "packages" / "aoa-demo" / "graph.json"

BOUND_SECONDS = 1.0
"""Measured at about 20 ms with parsing (research R6): far above it, so a slow machine passes, yet a quadratic comparison fails."""


def _edited(original: dict[str, Any]) -> tuple[dict[str, Any], Counts, Counts]:
    """A copy of the demo's graph with a few hundred edits of every kind, and the counts those edits must give."""
    graph = copy.deepcopy(original)
    nodes, edges = graph["nodes"], graph["edges"]
    relations = [edge for edge in edges if edge["type"] == "entity_relation"]
    entities = [node["id"] for node in nodes if node["type"] == "Entity"]
    for node in nodes[0:200]:
        node["label"] = node["label"] + " (renamed)"
    for node in nodes[200:300]:
        node["properties"]["note"] = {"nested": {"deep": True}}
    for edge in relations[:50]:
        edge["target_id"] = next(entity for entity in entities if entity != edge["target_id"])
    removed_ids = {node["id"] for node in nodes[-30:]}
    graph["nodes"] = [*nodes[:-30], *({"id": f"added.Node{i}", "type": "Entity", "label": f"N{i}", "properties": {}} for i in range(40))]
    gone_edges = [edge for edge in edges if edge["source_id"] in removed_ids or edge["target_id"] in removed_ids]
    graph["edges"] = [edge for edge in edges if edge not in gone_edges]
    changed_edges = sum(1 for edge in relations[:50] if edge not in gone_edges)
    return graph, Counts(added=40, removed=30, changed=300), Counts(added=0, removed=len(gone_edges), changed=changed_edges)


def test_two_versions_of_the_demo_graph_compare_within_the_bound() -> None:
    """Parsing both and comparing them stays under the bound; the counts equal the edits made."""
    original = json.loads(DEMO_GRAPH.read_text(encoding="utf-8"))
    assert len(original["nodes"]) > 3000
    newer, node_counts, edge_counts = _edited(original)
    older_text, newer_text = json.dumps(original), json.dumps(newer)

    started = time.perf_counter()
    result = compare(json.loads(older_text), json.loads(newer_text))
    elapsed = time.perf_counter() - started

    assert elapsed < BOUND_SECONDS
    assert result.node_counts == node_counts
    assert result.edge_counts == edge_counts
    assert sum(item.status is Status.UNCHANGED for item in result.nodes.values()) == len(original["nodes"]) - 330


def test_walking_every_action_of_the_demo_graph_stays_within_the_bound() -> None:
    """Every action's parts are walked in both documents, in far under the bound."""
    original = json.loads(DEMO_GRAPH.read_text(encoding="utf-8"))
    newer, _, _ = _edited(original)
    comparison = compare(original, newer)

    started = time.perf_counter()
    changed_inside(original, newer, comparison, root_type="Action", drawn_types={"Action", "Role"}, through={"generic:params", "generic:result"})
    elapsed = time.perf_counter() - started

    assert elapsed < BOUND_SECONDS
