# tests/graph_logical_contract/logical_golden_dump.py

"""Canonical G2-style dumps of ``rx.PyDiGraph`` logical graphs for golden tests (plan 009)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Final

import rustworkx as rx

_G2_VERTEX_KEYS: Final[frozenset[str]] = frozenset({"id", "vertex_type"})
_G2_EDGE_KEYS: Final[frozenset[str]] = frozenset(
    {"source_id", "target_id", "edge_type", "category"},
)


def g2_vertices_from_logical_rx(lg: rx.PyDiGraph) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for idx in lg.node_indices():
        data = lg[idx]
        row = {k: data[k] for k in _G2_VERTEX_KEYS}
        rows.append(row)
    return sorted(rows, key=lambda r: r["id"])


def g2_edges_from_logical_rx(lg: rx.PyDiGraph) -> list[dict[str, str]]:
    id_by_idx = {i: lg[i]["id"] for i in lg.node_indices()}
    rows: list[dict[str, str]] = []
    for s, t, w in lg.weighted_edge_list():
        rows.append(
            {
                "source_id": id_by_idx[s],
                "target_id": id_by_idx[t],
                "edge_type": w["edge_type"],
                "category": w["category"],
            },
        )
    return sorted(
        rows,
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def g2_snapshot_from_logical_rx(lg: rx.PyDiGraph) -> dict[str, Any]:
    return {"vertices": g2_vertices_from_logical_rx(lg), "edges": g2_edges_from_logical_rx(lg)}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def g2_snapshot_build_test_coordinator_clean_process() -> dict[str, Any]:
    """
    Build ``build_test_coordinator()`` in a **fresh** Python interpreter.

    Pytest pre-imports many modules; coordinator discovery walks intent subclasses,
    so an in-process ``build()`` can see a larger class closure than the G2 golden
    (which is defined for ``maxitor.test_domain.build._MODULES`` only).
    """
    root = _repo_root()
    env = {**os.environ, "PYTHONPATH": f"{root / 'src'}{os.pathsep}{root}"}
    script = """import importlib
import json

from maxitor.test_domain.build import _MODULES, build_test_coordinator

from tests.graph_logical_contract.logical_golden_dump import g2_snapshot_from_logical_rx

for name in _MODULES:
    importlib.import_module(name)
coord = build_test_coordinator()
print(json.dumps(g2_snapshot_from_logical_rx(coord.get_logical_graph())))
"""
    proc = subprocess.run(
        [sys.executable, "-"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(root),
        env=env,
    )
    if proc.returncode != 0:
        msg = f"G2 subprocess failed ({proc.returncode}): {proc.stderr}"
        raise RuntimeError(msg)
    return json.loads(proc.stdout.strip())


def load_g2_fixture(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "vertices" not in raw or "edges" not in raw:
        msg = "G2 fixture must contain top-level vertices and edges lists"
        raise ValueError(msg)
    return raw


def assert_g2_fixture_matches_snapshot(
    fixture: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    """Compare canonical G2 ``vertices`` / ``edges`` lists (fixture may include ``version``)."""
    expected_v = fixture["vertices"]
    expected_e = fixture["edges"]
    for row in expected_v:
        assert set(row) == _G2_VERTEX_KEYS, (
            f"vertex row must have exactly {_G2_VERTEX_KEYS!r}, got {set(row)!r}"
        )
    for row in expected_e:
        assert set(row) == _G2_EDGE_KEYS, (
            f"edge row must have exactly {_G2_EDGE_KEYS!r}, got {set(row)!r}"
        )
    if snapshot["vertices"] != expected_v:
        raise AssertionError(
            _first_list_mismatch("vertices", snapshot["vertices"], expected_v),
        )
    if snapshot["edges"] != expected_e:
        raise AssertionError(
            _first_list_mismatch("edges", snapshot["edges"], expected_e),
        )


def assert_g2_fixture_matches_rx(fixture: dict[str, Any], lg: rx.PyDiGraph) -> None:
    assert_g2_fixture_matches_snapshot(fixture, g2_snapshot_from_logical_rx(lg))


def _first_list_mismatch(
    label: str,
    actual: list[dict[str, str]],
    expected: list[dict[str, str]],
) -> str:
    if len(actual) != len(expected):
        return f"{label}: length {len(actual)} != {len(expected)}"
    for i, (a_row, e_row) in enumerate(zip(actual, expected, strict=True)):
        if a_row != e_row:
            return f"{label}[{i}]: {a_row!r} != {e_row!r}"
    return f"{label}: mismatch (unexpected)"
