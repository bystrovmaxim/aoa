# tests/graph_logical_contract/test_g4_dag_subgraph_golden.py

"""Golden **G4**: logical DAG slice vs ``dag_subgraph_test_domain.json``."""

from __future__ import annotations

from pathlib import Path

import pytest

from .logical_golden_dump import (
    assert_g4_fixture_matches_snapshot,
    g4_snapshot_build_test_coordinator_clean_process,
    load_g4_fixture,
)

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "golden_graph" / "dag_subgraph_test_domain.json"


@pytest.mark.graph_coverage
def test_g4_dag_subgraph_matches_golden() -> None:
    fixture = load_g4_fixture(_FIXTURE)
    snapshot = g4_snapshot_build_test_coordinator_clean_process()
    assert_g4_fixture_matches_snapshot(fixture, snapshot)


@pytest.mark.graph_coverage
def test_g4_dag_subgraph_snapshot_deterministic_across_clean_processes() -> None:
    a = g4_snapshot_build_test_coordinator_clean_process()
    b = g4_snapshot_build_test_coordinator_clean_process()
    assert a == b
