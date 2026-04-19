# tests/model/test_navigation_performance.py
"""
Navigation and template substitution benchmarks.

Reports use ``tests.bench.bench_report`` for multi-line stdout (default pytest
capture shows them; no ``-s`` required).
"""

from __future__ import annotations

import time

import pytest

from action_machine.context.context import Context
from action_machine.intents.logging.log_scope import LogScope
from action_machine.intents.logging.variable_substitutor import VariableSubstitutor
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from tests.bench.bench_report import (
    emit_benchmark_report,
    rows_compare_two_timings,
    rows_throughput_budget,
)

pytestmark = pytest.mark.benchmark

_RESOLVE_ITERATIONS = 10_000
_RESOLVE_BUDGET_SEC = 0.1
_SUBSTITUTE_ITERATIONS = 1_000
_SUBSTITUTE_BUDGET_SEC = 0.5
_FALSY_RATIO_LIMIT = 2.0


class TestNavigationPerformance:
    """Navigation benchmarks — evidence that caching is unnecessary."""

    def test_resolve_10k_calls_under_100ms(self, capsys: pytest.CaptureFixture[str]) -> None:
        """10,000 resolve() calls complete within 100 ms."""
        st = BaseState(nested={"deep": {"value": 42}})

        start = time.perf_counter()
        for _ in range(_RESOLVE_ITERATIONS):
            st.resolve("nested.deep.value")
        elapsed = time.perf_counter() - start

        emit_benchmark_report(
            capsys,
            "BaseState.resolve (nested path)",
            rows_throughput_budget(
                iterations=_RESOLVE_ITERATIONS,
                elapsed_sec=elapsed,
                budget_sec=_RESOLVE_BUDGET_SEC,
                quantity_label="resolve calls",
                throughput_label="calls/s",
            ),
        )

        assert elapsed < _RESOLVE_BUDGET_SEC, (
            f"10k resolve() took {elapsed:.3f}s (limit {_RESOLVE_BUDGET_SEC}s)"
        )

    def test_substitute_1k_calls_under_500ms(self, capsys: pytest.CaptureFixture[str]) -> None:
        """1,000 substitute() calls complete within 500 ms."""
        sub = VariableSubstitutor()
        scope = LogScope(machine="M", mode="t", action="A", aspect="a", nest_level=0)
        ctx = Context()
        st = BaseState(count=42)
        params = BaseParams()
        template = "User: {%context.user.user_id}, Count: {%state.count}"

        start = time.perf_counter()
        for _ in range(_SUBSTITUTE_ITERATIONS):
            sub.substitute(template, {}, scope, ctx, st, params)
        elapsed = time.perf_counter() - start

        emit_benchmark_report(
            capsys,
            "VariableSubstitutor.substitute (template with context/state)",
            rows_throughput_budget(
                iterations=_SUBSTITUTE_ITERATIONS,
                elapsed_sec=elapsed,
                budget_sec=_SUBSTITUTE_BUDGET_SEC,
                quantity_label="substitute calls",
                throughput_label="calls/s",
            ),
        )

        assert elapsed < _SUBSTITUTE_BUDGET_SEC, (
            f"1k substitute() took {elapsed:.3f}s (limit {_SUBSTITUTE_BUDGET_SEC}s)"
        )

    def test_resolve_falsy_values_same_speed_as_regular(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Falsy values (0, False, None) do not slow navigation."""
        st_regular = BaseState(value="hello")
        st_falsy = BaseState(value=0)

        start = time.perf_counter()
        for _ in range(_RESOLVE_ITERATIONS):
            st_regular.resolve("value")
        time_regular = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(_RESOLVE_ITERATIONS):
            st_falsy.resolve("value")
        time_falsy = time.perf_counter() - start

        emit_benchmark_report(
            capsys,
            "BaseState.resolve falsy vs regular (same path length)",
            rows_compare_two_timings(
                label_a="regular (str)",
                seconds_a=time_regular,
                label_b="falsy (int 0)",
                seconds_b=time_falsy,
                ratio_limit=_FALSY_RATIO_LIMIT,
            ),
        )

        assert time_falsy < time_regular * _FALSY_RATIO_LIMIT
