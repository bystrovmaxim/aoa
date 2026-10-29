# packages/maxitor/front/src/maxitor/front/model/core/resources/history_store.py
"""
HistoryStore — the histories Maxitor holds, one per name, as a resource actions are given.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A history someone opened is held once, for every reader of it, beside the graphs of its
versions in ``GraphStore`` (spec 037, research R7). A history is not a graph — it has no
DuckDB and no left panel — so it has a store of its own. The store bounds its cost: at
most ``max_histories`` entries; beyond that the one read longest ago leaves. It decides
nothing: whether a history is due for a check, or what a new list means, is an action's.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action aspect ──connections["HistoryStore"]──► HistoryStore
                        get / put / names / now / mark_checked / set_checking
"""

from __future__ import annotations

import time
from collections.abc import Callable

from maxitor.front.model.core.core_domain import CoreDomain
from maxitor.front.model.core.history_entry import HistoryEntry

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_controller import BaseController

#: Connection key under which actions receive the store.
HISTORY_STORE_CONNECTION_KEY = "HistoryStore"


@meta(description="The histories Maxitor holds, one per name", domain=CoreDomain)
class HistoryStore(BaseController):
    """
    AI-CORE-BEGIN
    ROLE: The one place that knows which histories this process holds.
    CONTRACT: ``put`` stores or replaces an entry by its name; ``get`` counts as a read, ``peek`` does not.
    INVARIANTS: At most ``max_histories`` entries; the least recently read leaves first; ``repr`` names no history and no key.
    AI-CORE-END
    """

    def __init__(self, *, max_histories: int = 50, clock: Callable[[], float] = time.monotonic) -> None:
        self._entries: dict[str, HistoryEntry] = {}
        self._max = max_histories
        self._clock = clock

    def __repr__(self) -> str:
        """Count the histories held, never name them."""
        return f"HistoryStore(held={len(self._entries)})"

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions use this same store."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the in-memory store is not a rollup target."""
        return False

    def now(self) -> float:
        """The store's clock, the one ``last_read`` and ``last_checked`` are measured on."""
        return self._clock()

    def get(self, name: str) -> HistoryEntry | None:
        """The entry held for ``name``, counted as a read, or ``None``."""
        entry = self._entries.get(name)
        if entry is not None:
            entry.last_read = self._clock()
        return entry

    def peek(self, name: str) -> HistoryEntry | None:
        """The entry held for ``name`` without counting it as a read, or ``None``."""
        return self._entries.get(name)

    def put(self, entry: HistoryEntry) -> None:
        """Store or replace ``entry``, evicting the least recently read one when full."""
        entry.last_read = self._clock()
        if entry.name not in self._entries and len(self._entries) >= self._max:
            oldest = min(self._entries, key=lambda name: self._entries[name].last_read)
            del self._entries[oldest]
        self._entries[entry.name] = entry

    def names(self) -> tuple[str, ...]:
        """The names of the histories held right now."""
        return tuple(self._entries)
