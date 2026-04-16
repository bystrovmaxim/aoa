# tests/graph_logical_contract/test_pr5_g2_logical_test_domain_golden.py

"""PR5 / **G2**: golden ``logical_test_domain.graph.json`` vs ``get_logical_graph()``."""

from __future__ import annotations

from pathlib import Path

import pytest

from .logical_golden_dump import (
    assert_g2_fixture_matches_snapshot,
    g2_snapshot_build_test_coordinator_clean_process,
    load_g2_fixture,
)

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "golden_graph" / "logical_test_domain.graph.json"


@pytest.mark.graph_coverage
def test_pr5_g2_logical_test_domain_matches_golden() -> None:
    fixture = load_g2_fixture(_FIXTURE)
    snapshot = g2_snapshot_build_test_coordinator_clean_process()
    assert_g2_fixture_matches_snapshot(fixture, snapshot)


@pytest.mark.graph_coverage
def test_pr5_c1_logical_g2_snapshot_deterministic_across_builds() -> None:
    """C1: two fresh interpreters yield identical canonical G2 snapshots."""
    a = g2_snapshot_build_test_coordinator_clean_process()
    b = g2_snapshot_build_test_coordinator_clean_process()
    assert a == b
