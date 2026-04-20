# tests/bench/test_scoped_logger_hot_path_bench.py
"""
Benchmarks: ``ScopedLogger`` / ``LogScope`` construction on the aspect hot path.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Anchor evidence that per-aspect ``ScopedLogger`` allocation (mirrors
``AspectExecutor.call``) is cheap relative to typical service work. Counters
claims that "N aspects × RPS" object counts alone imply a bottleneck: raw
construction throughput stays in the sub-millisecond range for thousands of
instances on CI-class hardware.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Uses the same ``ScopedLogger`` constructor path as production (aspect branch,
  not plugin).
- ``LogCoordinator(loggers=[])`` — no I/O; measures allocation + ``__init__``
  only, not emit.

"""

from __future__ import annotations

import time

import pytest

from action_machine.context.context import Context
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from tests.bench.bench_report import emit_benchmark_report, rows_throughput_budget

pytestmark = pytest.mark.benchmark

# Budgets are generous for cold CI; failure means a serious regression, not
# micro-optimization noise.
_SCOPED_LOGGER_10K_SEC = 0.35
_LOG_SCOPE_50K_SEC = 0.12
_SCOPED_LOGGER_ITERATIONS = 10_000
_LOG_SCOPE_ITERATIONS = 50_000


def test_10k_scoped_logger_constructions_under_budget(capsys: pytest.CaptureFixture[str]) -> None:
    """10k aspect-path ``ScopedLogger`` instances complete within budget."""
    coord = LogCoordinator(loggers=[])
    ctx = Context()
    state = BaseState()
    params = BaseParams()

    start = time.perf_counter()
    for i in range(_SCOPED_LOGGER_ITERATIONS):
        ScopedLogger(
            coordinator=coord,
            nest_level=0,
            machine_name="ActionProductMachine",
            mode="bench",
            action_name="bench.Action",
            aspect_name=f"aspect_{i % 5}",
            context=ctx,
            state=state,
            params=params,
            domain=None,
        )
    elapsed = time.perf_counter() - start

    emit_benchmark_report(
        capsys,
        "ScopedLogger construction (aspect path, no emit)",
        rows_throughput_budget(
            iterations=_SCOPED_LOGGER_ITERATIONS,
            elapsed_sec=elapsed,
            budget_sec=_SCOPED_LOGGER_10K_SEC,
            quantity_label="constructions",
            throughput_label="constructs/s",
        ),
    )

    assert elapsed < _SCOPED_LOGGER_10K_SEC, (
        f"10k ScopedLogger constructions took {elapsed:.3f}s "
        f"(limit {_SCOPED_LOGGER_10K_SEC}s)"
    )


def test_50k_log_scope_only_under_budget(capsys: pytest.CaptureFixture[str]) -> None:
    """``LogScope`` alone is lighter; 50k instances stay within budget."""
    start = time.perf_counter()
    for _ in range(_LOG_SCOPE_ITERATIONS):
        LogScope(
            machine="M",
            mode="bench",
            action="A",
            aspect="x",
            nest_level=0,
        )
    elapsed = time.perf_counter() - start

    emit_benchmark_report(
        capsys,
        "LogScope construction only",
        rows_throughput_budget(
            iterations=_LOG_SCOPE_ITERATIONS,
            elapsed_sec=elapsed,
            budget_sec=_LOG_SCOPE_50K_SEC,
            quantity_label="constructions",
            throughput_label="constructs/s",
        ),
    )

    assert elapsed < _LOG_SCOPE_50K_SEC, (
        f"50k LogScope constructions took {elapsed:.3f}s "
        f"(limit {_LOG_SCOPE_50K_SEC}s)"
    )
