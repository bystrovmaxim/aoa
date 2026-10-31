# packages/maxitor/front/tests/test_comparison_store.py
"""``ComparisonStore``: one computation per pair however many readers arrive together, a bounded number held, a refusal naming its version."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

import pytest
from maxitor.front.model.diagrams.resources.comparison_store import (
    ComparisonRefusedError,
    ComparisonStore,
    NotComparingError,
)


@dataclass
class _Held:
    """A held graph as the store sees it."""

    content_sha256: str
    document: str


def _graph(*labels: str) -> str:
    """A graph of one node per label, ids fixed by position."""
    return json.dumps({"schema_version": "1.1", "nodes": [{"id": f"n{at}", "label": label} for at, label in enumerate(labels)], "edges": []})


OLD, NEW = _Held("a" * 64, _graph("x", "y")), _Held("b" * 64, _graph("x", "z"))


async def test_readers_arriving_together_share_one_computation() -> None:
    """Ten reads of one pair at once: one computation, one result."""
    store = ComparisonStore(pair=lambda: (OLD, NEW))
    results = await asyncio.gather(*(store.current() for _ in range(10)))
    assert store.computed == 1
    assert all(result is results[0] for result in results)
    assert results[0].node_counts.changed == 1


async def test_at_most_capacity_pairs_are_held() -> None:
    """The pair read longest ago leaves; reading it again computes it again."""
    pairs = [(OLD, _Held(f"{n}" * 64, _graph("x", f"v{n}"))) for n in range(3)]
    current: list[tuple[_Held, _Held]] = []
    store = ComparisonStore(pair=lambda: current[0], capacity=2)
    for pair in [*pairs, pairs[0]]:
        current[:] = [pair]
        await store.current()
    assert (store.held, store.computed) == (2, 4)


async def test_a_graph_that_cannot_be_compared_is_refused_naming_its_version() -> None:
    """A broken A says A; a broken B says B."""
    broken = _Held("c" * 64, json.dumps({"schema_version": "9.9", "nodes": [], "edges": []}))
    for pair, side in (((broken, NEW), "A"), ((OLD, broken), "B")):
        with pytest.raises(ComparisonRefusedError, match=f"^{side}: Graph {side} has schema_version '9.9'"):
            await ComparisonStore(pair=lambda pair=pair: pair).current()


async def test_a_read_bound_to_no_pair_is_refused() -> None:
    """Outside a comparison read there is nothing to compare."""
    with pytest.raises(NotComparingError):
        await ComparisonStore(pair=lambda: None).current()
