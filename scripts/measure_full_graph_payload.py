#!/usr/bin/env python3
# scripts/measure_full_graph_payload.py
"""
Print full-graph JSON size metrics (PR-3): uncompressed UTF-8 + gzip(level=6).

Reproduces the methodology from ``archive/plan/019.md`` without requiring a live server.
Uses :func:`synthetic_sql_rows` plus a “fat” overlay that approximates the pre-PR1 payload shape.

Usage (from repository root)::

    uv run python scripts/measure_full_graph_payload.py
    uv run python scripts/measure_full_graph_payload.py --domains 12 --per-domain 40
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.maxitor.payload_wire_metrics import (  # noqa: E402
    simulate_pre_pr1_fat_payload,
    synthetic_sql_rows,
    uncompressed_and_gzip_len,
)

from aoa.maxitor.model.diagrams.actions.full_graph_action import (  # noqa: E402
    _build_payload_from_duckdb,
)
from aoa.maxitor.model.diagrams.actions.list_domains_action import (  # noqa: E402
    _LIST_DOMAINS_DISTINCT_COLORS,
)


class _RowsDuck:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def execute_fetch_dicts(self, _sql: str) -> list[dict]:
        return list(self._rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Measure interchange full-graph JSON wire sizes.")
    p.add_argument("--domains", type=int, default=8, help="Synthetic domain count (default 8)")
    p.add_argument(
        "--per-domain",
        type=int,
        default=25,
        help="Synthetic actions per domain (default 25)",
    )
    args = p.parse_args(argv)
    rows = synthetic_sql_rows(args.domains, args.per_domain)
    slim = _build_payload_from_duckdb(_RowsDuck(rows), _LIST_DOMAINS_DISTINCT_COLORS)
    fat = simulate_pre_pr1_fat_payload(slim)

    s_raw, s_gz = uncompressed_and_gzip_len(slim)
    f_raw, f_gz = uncompressed_and_gzip_len(fat)
    n_nodes = len(slim.get("nodes") or [])
    n_edges = len(slim.get("edges") or [])

    print("Interchange full-graph wire metrics (synthetic fixture; same topology for slim vs fat)")
    print(f"  Topology: domains={args.domains} actions_per_domain={args.per_domain} -> nodes={n_nodes} edges={n_edges}")
    print(f"  Slim:  uncompressed={s_raw:>8} B   gzip6={s_gz:>8} B")
    print(f"  Fat:   uncompressed={f_raw:>8} B   gzip6={f_gz:>8} B   (simulated legacy payload blobs)")
    if s_raw:
        print(f"  Ratio fat/slim: uncompressed ×{f_raw / s_raw:.2f}   gzip ×{f_gz / s_gz:.2f}")
    print()
    print("For production numbers, run the same metric on ``GET /api/v1/full-graph`` body from your DuckDB snapshot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
