# tests/bench/bench_report.py
"""
Human-readable stdout reports for load / benchmark tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Any test marked ``@pytest.mark.benchmark`` can call ``emit_benchmark_report`` so a
run is **self-describing**: what was measured, how many iterations, elapsed time,
budget, derived throughput, and pass/fail of the budget check — without relying on
a single dense log line.

Output is printed inside ``capsys.disabled()`` so it appears with default pytest
capture (no ``-s`` required).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from tests.bench.bench_report import emit_benchmark_report, rows_throughput_budget

    def test_foo(capsys):
        ...
        emit_benchmark_report(
            capsys,
            "My scenario",
            rows_throughput_budget(n=10_000, elapsed_sec=0.02, budget_sec=0.1),
        )

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Test-only benchmark reporting helpers.
CONTRACT: Multi-line blocks; optional throughput from iterations and elapsed time.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import pytest

_WIDTH = 72


def emit_benchmark_report(
    capsys: pytest.CaptureFixture[str],
    title: str,
    rows: list[tuple[str, str]],
) -> None:
    """Print a framed, label-aligned block to stdout (bypasses pytest capture)."""
    sep = "=" * _WIDTH
    lines = [sep, f"bench: {title}", sep]
    for label, value in rows:
        lines.append(f"  {label:<28} {value}")
    lines.append(sep)
    with capsys.disabled():
        print("\n".join(lines), end="\n\n")


def rows_throughput_budget(
    *,
    iterations: int,
    elapsed_sec: float,
    budget_sec: float,
    quantity_label: str = "iterations",
    throughput_label: str = "throughput",
) -> list[tuple[str, str]]:
    """Standard rows: counts, times, throughput, budget satisfaction."""
    rps = iterations / elapsed_sec if elapsed_sec > 0 else float("inf")
    under = elapsed_sec < budget_sec
    return [
        (quantity_label, f"{iterations:,}"),
        ("elapsed", f"{elapsed_sec:.4f} s"),
        ("wall budget", f"{budget_sec:.4f} s"),
        (throughput_label, f"{rps:,.0f} /s"),
        ("under budget", "yes" if under else "no"),
    ]


def rows_compare_two_timings(
    *,
    label_a: str,
    seconds_a: float,
    label_b: str,
    seconds_b: float,
    ratio_limit: float,
) -> list[tuple[str, str]]:
    """Two elapsed times plus ratio check (e.g. falsy vs regular paths)."""
    ratio = seconds_b / seconds_a if seconds_a > 0 else float("inf")
    ok = seconds_b < seconds_a * ratio_limit
    return [
        (f"elapsed ({label_a})", f"{seconds_a:.4f} s"),
        (f"elapsed ({label_b})", f"{seconds_b:.4f} s"),
        (f"ratio ({label_b}/{label_a})", f"{ratio:.3f}x"),
        ("ratio limit", f"< {ratio_limit:.1f}x"),
        ("under ratio limit", "yes" if ok else "no"),
    ]
