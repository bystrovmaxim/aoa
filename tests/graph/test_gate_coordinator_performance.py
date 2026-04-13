# tests/graph/test_gate_coordinator_performance.py
"""PR-T14: regression anchor for GateCoordinator register+build (graph assembly)."""

from __future__ import annotations

import time

import pytest

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.graph.payload import FacetPayload

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


def test_many_cold_gate_coordinator_builds_under_budget() -> None:
    """Fresh ``register().build()`` per iteration; loose limit for varied runners."""
    n = 300
    start = time.perf_counter()
    for _ in range(n):
        GateCoordinator().register(_PerfInspector).build()
    elapsed = time.perf_counter() - start

    assert elapsed < 3.0, (
        f"{n} cold GateCoordinator register+build cycles took {elapsed:.3f}s "
        f"(limit 3.0s)"
    )
