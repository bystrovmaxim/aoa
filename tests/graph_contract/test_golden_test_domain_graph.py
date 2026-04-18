# tests/graph_contract/test_golden_test_domain_graph.py

"""G2-style interchange snapshot: determinism for ``build_sample_coordinator()`` graph."""

from __future__ import annotations

import pytest

from .golden_dump import g2_snapshot_build_sample_coordinator_clean_process


@pytest.mark.graph_coverage
def test_samples_graph_snapshot_deterministic_across_clean_processes() -> None:
    """Two fresh interpreters yield identical snapshots."""
    a = g2_snapshot_build_sample_coordinator_clean_process()
    b = g2_snapshot_build_sample_coordinator_clean_process()
    assert a == b
