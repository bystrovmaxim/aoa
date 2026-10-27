# packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/graph_fingerprint_action.py
"""
GraphFingerprintAction — the fingerprint of the graph held for a source, from memory.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A tab outside a room asks every 30 seconds whether the graph it drew is still the one Maxitor
holds (spec 028, FR-076). The answer comes from memory at once. Asking also marks the tab as open,
so the source is checked on the clock while it is looked at (FR-071); and when its last check is
older than its interval — a source nobody watched for a while — a check starts in the background,
so the next answer is current (FR-073).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/graph-fingerprint?source=… ──► OpenTabs.seen ──► fingerprint from GraphStore
                                                      └─ due? ──► SourceChecks.run_soon(CheckSourceAction)
"""

from __future__ import annotations

from typing import cast

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.actions.check_source_action import CheckSourceAction, CheckSourceParams
from aoa.maxitor.model.core.core_domain import CoreDomain
from aoa.maxitor.model.core.freshness import is_due
from aoa.maxitor.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from aoa.maxitor.model.core.resources.open_tabs_registry import OPEN_TABS_CONNECTION_KEY, OpenTabsRegistry
from aoa.maxitor.model.core.resources.source_checks import SOURCE_CHECKS_CONNECTION_KEY, SourceChecks


class GraphFingerprintParams(BaseParams):
    """The source a tab shows."""

    source: str = Field(description="graph-json address the tab shows")


class GraphFingerprintResult(BaseResult):
    """The fingerprint of the graph held for the source."""

    fingerprint: str = Field(description="SHA-256 of the graph-json body the held graph is built from")


@meta(description="Answer the held graph's fingerprint and keep its source checked while a tab shows it", domain=CoreDomain)
@check_roles(GuestRole)
@connection(GraphStoreController, key=GRAPH_STORE_CONNECTION_KEY, description="Built graphs")
@connection(OpenTabsRegistry, key=OPEN_TABS_CONNECTION_KEY, description="Tabs outside rooms")
@connection(SourceChecks, key=SOURCE_CHECKS_CONNECTION_KEY, description="Runs a check in the background")
class GraphFingerprintAction(BaseAction[GraphFingerprintParams, GraphFingerprintResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer from memory which graph Maxitor holds for a source, and keep that source watched.
    CONTRACT: Marks the tab open; answers the held fingerprint at once; starts a background check when due.
    INVARIANTS: Never waits for the service; never logs who asked.
    AI-CORE-END
    """

    @summary_aspect("Mark the tab open, answer the fingerprint, start a due check")
    async def fingerprint_summary(
        self,
        params: GraphFingerprintParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> GraphFingerprintResult:
        """Answer the held fingerprint; schedule a check when the source is due."""
        store = cast(GraphStoreController, connections[GRAPH_STORE_CONNECTION_KEY])
        tabs = cast(OpenTabsRegistry, connections[OPEN_TABS_CONNECTION_KEY])
        checks = cast(SourceChecks, connections[SOURCE_CHECKS_CONNECTION_KEY])
        now = store.now()
        tabs.seen(params.source, now)
        entry = await store.acquire(params.source)
        if is_due(entry, now):
            checks.run_soon(CheckSourceAction, CheckSourceParams(source=params.source))
        return GraphFingerprintResult(fingerprint=entry.fingerprint)
