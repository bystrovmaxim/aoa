# tests/graph_contract/test_golden_dag_subgraph_test_domain.py

"""G4-style DAG slice snapshot: determinism across clean processes."""

from __future__ import annotations

import pytest

from .golden_dump import g4_snapshot_build_sample_coordinator_clean_process


@pytest.mark.graph_coverage
def test_dag_subgraph_snapshot_deterministic_across_clean_processes() -> None:
    a = g4_snapshot_build_sample_coordinator_clean_process()
    b = g4_snapshot_build_sample_coordinator_clean_process()
    assert a == b
