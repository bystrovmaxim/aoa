# tests/graph_logical_contract/test_golden_logical_minimal_g0.py

"""
Golden **G0**: ``logical_minimal.json`` vs ``build_from_g0_input``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Lock the minimal logical graph interchange shape and the G0 builder output before
``GateCoordinator`` integration.

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

from action_machine.graph.logical import LogicalEdge, LogicalVertex, build_from_g0_input

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "golden_graph" / "logical_minimal.json"


def _canonical_vertices(vertices: list[LogicalVertex]) -> list[dict]:
    rows = [asdict(v) for v in vertices]
    return sorted(rows, key=lambda r: r["id"])


def _canonical_edges(edges: list[LogicalEdge]) -> list[dict]:
    rows = [asdict(e) for e in edges]
    return sorted(
        rows,
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def test_logical_minimal_g0_matches_golden() -> None:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    inp = raw["input"]
    expected = raw["expected"]

    vertices, edges = build_from_g0_input(inp)

    got_v = _canonical_vertices(vertices)
    got_e = _canonical_edges(edges)

    exp_v = sorted(expected["vertices"], key=lambda r: r["id"])
    exp_e = sorted(
        expected["edges"],
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )

    assert got_v == exp_v
    assert got_e == exp_e


def test_logical_minimal_g0_rejects_unknown_domain() -> None:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    inp = dict(raw["input"])
    inp["actions"] = [
        {
            "id": "golden_demo.actions.DemoAction",
            "display_name": "DemoAction",
            "domain_id": "missing.domain.X",
        },
    ]
    with pytest.raises(ValueError, match="unknown domain_id"):
        build_from_g0_input(inp)
