# packages/maxitor/src/maxitor/viewer/model/core/resources/open_tabs_registry.py
"""
OpenTabsRegistry — when a tab outside a room last asked about a source.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor checks a held source on a timer only while someone looks at it (spec 028, FR-071,
FR-073). A tab inside a room is known to the room registry; a tab outside one asks for the
graph fingerprint every 30 seconds, and this registry remembers when each source was last
asked. Whether that still counts as an open tab is decided by the action that asks.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GraphFingerprintAction ──seen(source, now)──► OpenTabsRegistry
    CheckDueSourcesAction  ──last_seen(source)──► OpenTabsRegistry
"""

from __future__ import annotations

from maxitor.viewer.model.core.core_domain import CoreDomain

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_controller import BaseController

#: Connection key under which actions receive the registry.
OPEN_TABS_CONNECTION_KEY = "OpenTabs"


@meta(description="When a tab outside a room last asked about each source", domain=CoreDomain)
class OpenTabsRegistry(BaseController):
    """
    AI-CORE-BEGIN
    ROLE: Remember, per source, the last time a tab outside a room asked for its fingerprint.
    CONTRACT: ``seen`` records a time; ``last_seen`` returns it, or ``None`` for a source never asked about.
    INVARIANTS: Decides nothing — how long a tab counts as open is the asking action's rule.
    AI-CORE-END
    """

    def __init__(self) -> None:
        self._seen: dict[str, float] = {}

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions use this same registry."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the in-memory registry is not a rollup target."""
        return False

    def seen(self, source: str, when: float) -> None:
        """Record that a tab asked about ``source`` at ``when``."""
        self._seen[source] = when

    def last_seen(self, source: str) -> float | None:
        """When a tab last asked about ``source``, or ``None``."""
        return self._seen.get(source)
