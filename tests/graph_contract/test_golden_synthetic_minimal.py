# tests/graph_contract/test_golden_synthetic_minimal.py

"""
Golden: ``synthetic_minimal.json`` vs ``build_from_synthetic_bundle``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Lock the minimal interchange shape and the synthetic-bundle builder output before
``GraphCoordinator`` integration.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Comparison uses canonical sorted JSON (deterministic).
- Fixture path is stable relative to this test module.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from action_machine.graph import GraphEdge, GraphVertex, build_from_synthetic_bundle

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "golden_graph" / "synthetic_minimal.json"


def _canonical_vertices(vertices: list[GraphVertex]) -> list[dict]:
    rows = [asdict(v) for v in vertices]
    return sorted(rows, key=lambda r: r["id"])


def _canonical_edges(edges: list[GraphEdge]) -> list[dict]:
    rows = [asdict(e) for e in edges]
    return sorted(
        rows,
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def test_synthetic_minimal_matches_golden() -> None:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    inp = raw["input"]
    expected = raw["expected"]

    vertices, edges = build_from_synthetic_bundle(inp)

    got_v = _canonical_vertices(vertices)
    got_e = _canonical_edges(edges)

    exp_v = sorted(expected["vertices"], key=lambda r: r["id"])
    exp_e = sorted(
        expected["edges"],
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )

    assert got_v == exp_v
    assert got_e == exp_e


def test_synthetic_minimal_rejects_unknown_edge_target() -> None:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    inp = dict(raw["input"])
    inp["edges"] = [
        *inp["edges"],
        {
            "source_id": "golden_demo.actions.DemoAction",
            "target_id": "no.such.vertex",
            "edge_type": "CONNECTS_TO",
            "stereotype": "X",
            "category": "direct",
            "is_dag": True,
            "attributes": {},
        },
    ]
    with pytest.raises(ValueError, match="unknown target_id"):
        build_from_synthetic_bundle(inp)
