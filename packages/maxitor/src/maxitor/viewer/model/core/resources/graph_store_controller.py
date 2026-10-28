# packages/maxitor/src/maxitor/viewer/model/core/resources/graph_store_controller.py
"""
GraphStoreController — the store of built graphs, as a resource actions are given.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor keeps one built graph per source in its ``GraphStore``. New code — the checks
that keep a graph fresh, the rooms that report which graph a tab drew — reaches that
store only through this resource, never directly: the store is state the process owns,
and state is touched from actions only through a resource. The controller adds no
rules of its own; whether a source is due for a check, or a build may replace an entry,
is decided in an action.

The older routes of #214 still read the store directly; moving them is #278.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action aspect ──connections["GraphStore"]──► GraphStoreController ──► GraphStore
                                                         │
                         entry / acquire / replace / held_sources / mark_checked / checking
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxitor.viewer.model.core.core_domain import CoreDomain

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_controller import BaseController

if TYPE_CHECKING:
    from maxitor.viewer.api.graph_store import GraphEntry, GraphStore

#: Connection key under which actions receive the controller.
GRAPH_STORE_CONNECTION_KEY = "GraphStore"


@meta(description="The store of built graphs, one per source", domain=CoreDomain)
class GraphStoreController(BaseController):
    """
    AI-CORE-BEGIN
    ROLE: The resource through which actions read, rebuild and mark the graphs Maxitor holds.
    CONTRACT: Every method delegates to the one ``GraphStore`` of the process; ``replace`` swaps an
    entry only when its build succeeds, as ``GraphStore.reload`` does.
    INVARIANTS: Decides nothing; ``entry`` never counts as a read, so a check does not keep a graph alive.
    AI-CORE-END
    """

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions use this same controller."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the in-memory store is not a rollup target."""
        return False

    def entry(self, source: str) -> GraphEntry | None:
        """Return the entry held for ``source`` without counting it as a read, or ``None``."""
        return self._store.peek(source)

    async def acquire(self, source: str) -> GraphEntry:
        """Return the entry for ``source``, building it when it is not held."""
        return await self._store.acquire(source)

    async def replace(self, source: str) -> GraphEntry:
        """Build ``source`` again and swap the entry in only when the build succeeds."""
        return await self._store.reload(source)

    def now(self) -> float:
        """The store's clock, the one ``last_checked`` is measured on."""
        return self._store.now()

    def held_sources(self) -> tuple[str, ...]:
        """Return the sources held right now."""
        return self._store.held_sources()

    def mark_checked(self, source: str, when: float) -> None:
        """Record that ``source`` was asked whether its graph changed at ``when``."""
        entry = self._store.peek(source)
        if entry is not None:
            entry.last_checked = when

    def is_checking(self, source: str) -> bool:
        """Whether a check of ``source`` is running now."""
        entry = self._store.peek(source)
        return entry is not None and entry.checking

    def set_checking(self, source: str, checking: bool) -> None:
        """Record that a check of ``source`` started (``True``) or ended (``False``)."""
        entry = self._store.peek(source)
        if entry is not None:
            entry.checking = checking
