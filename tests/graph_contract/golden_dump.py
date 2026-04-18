# tests/graph_contract/golden_dump.py

"""Canonical G2-style interchange snapshots and G4-style DAG payloads for subprocess tests."""

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


def g2_vertices_from_rx(lg: rx.PyDiGraph) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for idx in lg.node_indices():
        data = lg[idx]
        row = {k: data[k] for k in _G2_VERTEX_KEYS}
        rows.append(row)
    return rows


def g2_edges_from_rx(lg: rx.PyDiGraph) -> list[dict[str, str]]:
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
    return rows


def g2_snapshot_from_interchange_rx(lg: rx.PyDiGraph) -> dict[str, Any]:
    return {"vertices": g2_vertices_from_rx(lg), "edges": g2_edges_from_rx(lg)}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def g2_snapshot_build_sample_coordinator_clean_process() -> dict[str, Any]:
    """
    Build ``build_sample_coordinator()`` in a **fresh** Python interpreter.

    Pytest pre-imports many modules; coordinator discovery walks intent subclasses,
    so an in-process ``build()`` can see a larger class closure than a subprocess
    that only imports ``maxitor.samples.build._MODULES``.
    """
    root = _repo_root()
    env = {**os.environ, "PYTHONPATH": f"{root / 'src'}{os.pathsep}{root}"}
    script = """import importlib
import json

from maxitor.samples.build import _MODULES, build_sample_coordinator

from tests.graph_contract.golden_dump import g2_snapshot_from_interchange_rx

for name in _MODULES:
    importlib.import_module(name)
coord = build_sample_coordinator()
print(json.dumps(g2_snapshot_from_interchange_rx(coord.get_graph())))
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


def g4_snapshot_build_sample_coordinator_clean_process() -> dict[str, Any]:
    """Same isolation rationale as :func:`g2_snapshot_build_sample_coordinator_clean_process`."""
    root = _repo_root()
    env = {**os.environ, "PYTHONPATH": f"{root / 'src'}{os.pathsep}{root}"}
    script = """import importlib
import json

from action_machine.graph.dag import (
    dag_edge_pairs_from_rx,
    dag_subgraph_is_acyclic_from_rx,
)
from maxitor.samples.build import _MODULES, build_sample_coordinator

for name in _MODULES:
    importlib.import_module(name)
coord = build_sample_coordinator()
lg = coord.get_graph()
pairs = dag_edge_pairs_from_rx(lg)
edges = [{"source_id": s, "target_id": t} for s, t in pairs]
print(
    json.dumps(
        {"dag_edges": edges, "acyclic_expected": dag_subgraph_is_acyclic_from_rx(lg)},
    ),
)
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
        msg = f"G4 subprocess failed ({proc.returncode}): {proc.stderr}"
        raise RuntimeError(msg)
    return json.loads(proc.stdout.strip())
