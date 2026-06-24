# tests/maxitor/test_full_graph_payload_metrics.py
"""PR-3: slim full-graph JSON is smaller on the wire than a pre-PR1 fat simulation (same topology)."""

from __future__ import annotations

from typing import Any

from aoa.maxitor.model.diagrams.actions.full_graph_action import _build_payload_from_duckdb
from aoa.maxitor.model.diagrams.actions.list_domains_action import _LIST_DOMAINS_DISTINCT_COLORS

from .payload_wire_metrics import (
    simulate_pre_pr1_fat_payload,
    synthetic_sql_rows,
    uncompressed_and_gzip_len,
)


class _RowsDuck:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def execute_fetch_dicts(self, _sql: str) -> list[dict[str, Any]]:
        return list(self._rows)


def test_slim_full_graph_smaller_than_fat_simulation_same_topology() -> None:
    rows = synthetic_sql_rows(num_domains=8, actions_per_domain=25)
    slim = _build_payload_from_duckdb(_RowsDuck(rows), _LIST_DOMAINS_DISTINCT_COLORS)
    fat = simulate_pre_pr1_fat_payload(slim)

    slim_raw, slim_gz = uncompressed_and_gzip_len(slim)
    fat_raw, fat_gz = uncompressed_and_gzip_len(fat)

    assert slim_raw < fat_raw, "slim uncompressed should beat fat overlay on same graph"
    assert slim_gz < fat_gz, "slim gzip should beat fat overlay on same graph"
    assert fat_raw > slim_raw * 2, "fat simulation should be substantially larger (regression guard)"
