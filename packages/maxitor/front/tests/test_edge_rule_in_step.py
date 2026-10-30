# packages/maxitor/front/tests/test_edge_rule_in_step.py
"""The comparison's copy of the edge id rule gives AOA's id for every edge of the demo's graph (spec 038, FR-006)."""

from __future__ import annotations

import json
from pathlib import Path

from maxitor.graph_compare.edge_ids import edge_id as compared_edge_id

from aoa.action_machine.graph.edge_identity import edge_id as aoa_edge_id

DEMO_GRAPH = Path(__file__).resolve().parents[3] / "aoa-demo" / "graph.json"


def test_the_copied_rule_equals_aoas_on_every_demo_edge() -> None:
    """``maxitor.graph_compare`` may not import AOA, so it keeps a copy; this is where the two meet."""
    edges = json.loads(DEMO_GRAPH.read_text(encoding="utf-8"))["edges"]
    kinds = {edge["type"] for edge in edges}
    assert {"entity_relation", "lifecycle_transition"} <= kinds
    for edge in edges:
        row = {key: value for key, value in edge.items() if key != "id"}
        assert compared_edge_id(row) == aoa_edge_id(row) == edge["id"]
