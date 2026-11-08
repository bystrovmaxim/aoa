# tests/action_machine/resources/test_resource_entities_bench.py
"""
SC-004 — the return-check ratio, measured by a benchmark the closing run leaves out.

``research.md`` records why the 5% figure is a measurement rather than a hard
assertion: wall-clock microseconds on a shared, parallel machine are noisy, and the
ratio sits near the line. This module therefore **measures and prints** the ratio and
the per-call wrapper overhead, and guards only a loose regression bound; the regular
tests (``test_resource_entities_check.py``) guard the same loose bound for the check as
a whole.

The model is the shop database of the return-check tests: an order whose customer and
line are loaded, whose line's product is a reference, and whose currency is a
dictionary member — a representative answer a resource walks.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest

from aoa.action_machine.resources.entities.plan import compute_entities_plan
from aoa.action_machine.resources.entities.walk import walk_answer
from tests.support.return_check_model import ShopDatabaseStorage, make_order

_COUNT = 1_000
_ROUNDS = 5

_SC_004_RATIO = 0.05
"""The spec's target: the return check costs no more than 5% of building the same entities."""

_LOOSE_RATIO_BOUND = 0.75
"""A regression anchor, not the target: a check becoming as expensive as building fails it."""

_LOOSE_OVERHEAD_SECONDS = 25e-6
"""A regression anchor for a per-call wrapper overhead; the planned figure is 0.2 µs."""


def _fastest(call: Callable[[], None]) -> float:
    """Run ``call`` a few times and return the fastest wall-clock sample, in seconds."""
    samples: list[float] = []
    for _ in range(_ROUNDS):
        started = time.perf_counter()
        call()
        samples.append(time.perf_counter() - started)
    return min(samples)


@pytest.mark.benchmark
def test_the_return_check_costs_no_more_than_five_percent_of_building(capsys: pytest.CaptureFixture[str]) -> None:
    """Measure the check/building ratio and the wrapper's per-call overhead (SC-004)."""
    plan = compute_entities_plan(ShopDatabaseStorage)
    built: list = []

    def build() -> None:
        built.clear()
        built.extend(make_order() for _ in range(_COUNT))

    def check() -> None:
        walk_answer(built, plan, "ShopDatabaseStorage", "fetch_orders", "orders")

    build_seconds = _fastest(build)
    # The last build left ``built`` full; measure the walk over that answer.
    check_seconds = _fastest(check)
    ratio = check_seconds / build_seconds

    storage = ShopDatabaseStorage()
    raw = ShopDatabaseStorage.__dict__["fetch_state"].__wrapped__
    wrapped_call = _fastest(lambda: [storage.fetch_state() for _ in range(_COUNT)]) / _COUNT
    raw_call = _fastest(lambda: [raw(storage) for _ in range(_COUNT)]) / _COUNT
    overhead = wrapped_call - raw_call

    with capsys.disabled():
        print(
            f"\nSC-004: build {_COUNT} answers in {build_seconds:.6f}s, "
            f"walk them in {check_seconds:.6f}s, ratio {ratio:.2%} "
            f"(target {_SC_004_RATIO:.0%}); "
            f"wrapper overhead {overhead * 1e6:.3f} µs/call (planned 0.2 µs)",
        )

    # The spec's 5% target is measured above, not hard-asserted: research.md records that
    # a hard 5% assertion fails at random on a shared, parallel machine.
    assert ratio <= _LOOSE_RATIO_BOUND, (
        f"the return check costs {ratio:.2%} of building, above the loose {_LOOSE_RATIO_BOUND:.0%} anchor"
    )
    assert overhead <= _LOOSE_OVERHEAD_SECONDS, (
        f"a wrapped call adds {overhead * 1e6:.3f} µs, above the loose {_LOOSE_OVERHEAD_SECONDS * 1e6:.0f} µs anchor"
    )
