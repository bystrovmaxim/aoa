# packages/maxitor/front/src/maxitor/front/model/diagrams/resources/comparison_store.py
"""
ComparisonStore — the comparison of the two versions a read names, computed once per pair.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A comparison read names two held versions, B as ``source`` and A as ``a`` (spec 038,
FR-018 – FR-020). Comparing them is ``maxitor.graph_compare.compare`` over the graphs'
texts; this resource does it once per pair, however many readers ask, and holds the
result. A pair is named by the SHA-256 of what each graph was built from, not by its
source: when Live is rebuilt its content changes, so the next read is a new pair and is
compared afresh, and an old pair is never wrong — only no longer asked for.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action ──current()──► pair() (the two entries the request is bound to)
                              │
                              ▼
                 (sha A, sha B) held? ──yes──► Comparison
                              │
                              └─no──► one lock per pair ──► compare(json A, json B) in a thread
                                                              + changed_inside
                                                              ──► held, at most ``capacity`` pairs,
                                                                  the one read longest ago leaving

The two entries come from ``pair``, a callable the application hands in — it reads the
request's bindings, which belong to the web layer, so this resource never imports it.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, Protocol

from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.graph_compare import ChangedPart, Comparison, GraphNotComparableError, changed_inside, compare

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_controller import BaseController

#: Connection key under which the comparison actions receive the store.
COMPARISON_STORE_CONNECTION_KEY = "Comparisons"

#: How many compared pairs are held at once.
DEFAULT_CAPACITY = 32

#: What a use-case diagram draws: an action's parts are everything else it owns or links to (spec 041, research R1).
ACTION_TYPE = "Action"
DRAWN_TYPES = frozenset({"Action", "Role"})
THROUGH_EDGES = frozenset({"generic:params", "generic:result"})

#: Each action's changed parts, by action id.
ChangedInside = dict[str, tuple[ChangedPart, ...]]


class ComparedGraph(Protocol):
    """What a held graph offers a comparison: what it was built from, and its text."""

    content_sha256: str
    document: str


class ComparisonRefusedError(ValueError):
    """One of the two graphs cannot be compared; the message names which version and why."""


class NotComparingError(LookupError):
    """The read is not bound to two versions."""


@meta(description="The comparison of two held versions, computed once per pair", domain=DiagramsDomain)
class ComparisonStore(BaseController):
    """
    AI-CORE-BEGIN
    ROLE: Compare the two versions the current read names, once per pair, and hold the result.
    CONTRACT: ``current()`` returns the ``Comparison`` of A with B for the read it serves, ``changed_inside()`` each action's changed parts; a graph that cannot be compared raises ``ComparisonRefusedError`` naming the version.
    INVARIANTS: A pair is keyed by both graphs' content, so a rebuilt Live is a new pair; at most ``capacity`` pairs are held; one computation per pair at a time; ``computed`` counts the computations made.
    AI-CORE-END
    """

    def __init__(self, pair: Callable[[], tuple[ComparedGraph, ComparedGraph] | None], capacity: int = DEFAULT_CAPACITY) -> None:
        self._pair = pair
        self._capacity = capacity
        self._held: OrderedDict[tuple[str, str], tuple[Comparison, ChangedInside]] = OrderedDict()
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}
        self.computed = 0
        """How many comparisons were computed, not served from what is held."""
        self.last_milliseconds = 0.0
        """How long the last computation took."""

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions use this same store."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the in-memory store is not a rollup target."""
        return False

    @property
    def held(self) -> int:
        """How many pairs are held now."""
        return len(self._held)

    async def current(self) -> Comparison:
        """The comparison of the read's A with its B, computed on the first read of the pair."""
        return (await self._read())[0]

    async def changed_inside(self) -> ChangedInside:
        """What changed inside each action of the read's pair, computed with its comparison."""
        return (await self._read())[1]

    async def _read(self) -> tuple[Comparison, ChangedInside]:
        """The read's pair as held, computed on its first read."""
        pair = self._pair()
        if pair is None:
            raise NotComparingError("This read names no two versions to compare.")
        older, newer = pair
        key = (older.content_sha256, newer.content_sha256)
        held = self._held.get(key)
        if held is not None:
            self._held.move_to_end(key)
            return held
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            held = self._held.get(key)
            if held is None:
                started = time.perf_counter()
                held = await asyncio.to_thread(_compared, older.document, newer.document)
                self.last_milliseconds = (time.perf_counter() - started) * 1000
                self.computed += 1
                self._held[key] = held
                while len(self._held) > self._capacity:
                    self._held.popitem(last=False)
            self._held.move_to_end(key)
        self._locks.pop(key, None)
        return held


def _compared(older: str, newer: str) -> tuple[Comparison, ChangedInside]:
    """Parse both texts, compare them and walk the actions; a refusal names the version it came from."""
    documents: list[Any] = []
    for side, text in (("A", older), ("B", newer)):
        try:
            documents.append(json.loads(text))
        except ValueError as exc:
            raise ComparisonRefusedError(f"{side}: the graph is not JSON: {exc}") from exc
    try:
        comparison = compare(documents[0], documents[1])
        return comparison, changed_inside(documents[0], documents[1], comparison, root_type=ACTION_TYPE, drawn_types=DRAWN_TYPES, through=THROUGH_EDGES)
    except GraphNotComparableError as exc:
        raise ComparisonRefusedError(f"{_refused_side(documents[0])}: {exc}") from exc


def _refused_side(older: Any) -> str:
    """Which version a refusal came from: A when A cannot be compared even with itself, else B."""
    try:
        compare(older, older)
    except GraphNotComparableError:
        return "A"
    return "B"
