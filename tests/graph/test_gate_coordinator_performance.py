# tests/graph/test_gate_coordinator_performance.py
"""PR-T14: regression anchor for GraphCoordinator register+build (graph assembly)."""

from __future__ import annotations

import time

import pytest

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.graph.payload import FacetPayload
from tests.bench.bench_report import emit_benchmark_report, rows_throughput_budget

pytestmark = pytest.mark.benchmark


class _PerfLeaf:
    """Single discoverable class for a minimal inspector walk."""


class _PerfInspector(BaseIntentInspector):
    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return [_PerfLeaf]

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        return FacetPayload(
            node_type="perf",
            node_name="P",
            node_class=target_cls,
        )

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        raise NotImplementedError


_BUILD_CYCLES = 300
_WALL_BUDGET_SEC = 3.0


def test_many_cold_gate_coordinator_builds_under_budget(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fresh ``register().build()`` per iteration; loose limit for varied runners."""
    start = time.perf_counter()
    for _ in range(_BUILD_CYCLES):
        GraphCoordinator().register(_PerfInspector).build()
    elapsed = time.perf_counter() - start

    emit_benchmark_report(
        capsys,
        "GraphCoordinator cold register + build (per cycle)",
        rows_throughput_budget(
            iterations=_BUILD_CYCLES,
            elapsed_sec=elapsed,
            budget_sec=_WALL_BUDGET_SEC,
            quantity_label="cycles (register+build)",
            throughput_label="cycles/s",
        ),
    )

    assert elapsed < _WALL_BUDGET_SEC, (
        f"{_BUILD_CYCLES} cold GraphCoordinator register+build cycles took {elapsed:.3f}s "
        f"(limit {_WALL_BUDGET_SEC}s)"
    )
