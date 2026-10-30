# packages/maxitor/front/src/maxitor/front/model/core/actions/check_source_action.py
"""
CheckSourceAction — ask a service whether its graph changed, and rebuild it when it did.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A held graph stays current only if someone asks its service (spec 028, FR-071 … FR-075). One
check asks once: with the held body's ``ETag`` / ``Last-Modified`` when the service gave them, so
an unchanged service answers ``304``; without them it downloads and compares the SHA-256 with the
one the held graph was built from. A changed source is rebuilt through the store, which swaps the
new graph in only when its build succeeds, and every room of the source is told the new
fingerprint. An unreachable source or a failed build keeps the graph everyone already has. Checks
of one source never overlap: a second one finds the first running and returns.

``force`` skips the question and rebuilds at once: **Reload** inside a room (FR-065, FR-077).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    source ──held? checking?──► GraphSource.fetch_if_changed(held validators)
        ├─ NotModified / same SHA-256 ──► mark_checked ── "unchanged"
        ├─ new body ──► GraphStore.replace ──► graph_changed to every room ── "rebuilt"
        ├─ build fails ──► old graph kept ── "failed"
        └─ Unreachable ──► old graph kept ── "unreachable"
"""

from __future__ import annotations

from typing import Literal, cast

from maxitor.front.api.graph_store import GraphBuildError, GraphEntry, GraphStoreBusyError
from maxitor.front.model.core.core_domain import CoreDomain
from maxitor.front.model.core.resources.graph_source_gateway import (
    GRAPH_SOURCE_CONNECTION_KEY,
    Document,
    GraphSourceGateway,
    Unreachable,
)
from maxitor.front.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from maxitor.front.model.core.source_label import label
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

CheckStatus = Literal["unchanged", "rebuilt", "failed", "unreachable", "skipped", "not_held"]


class CheckSourceParams(BaseParams):
    """The source to check."""

    source: str = Field(description="graph-json address of the held source")
    force: bool = Field(default=False, description="Rebuild without asking whether it changed (Reload)")


class CheckSourceResult(BaseResult):
    """What the check found, and the fingerprint held afterwards."""

    status: CheckStatus = Field(description="unchanged, rebuilt, failed, unreachable, skipped or not_held")
    fingerprint: str = Field(default="", description="SHA-256 of the body the held graph is built from")


@meta(description="Ask a service whether its graph changed and rebuild it when it did", domain=CoreDomain)
@check_roles(GuestRole)
@connection(GraphStoreController, key=GRAPH_STORE_CONNECTION_KEY, description="Built graphs")
@connection(GraphSourceGateway, key=GRAPH_SOURCE_CONNECTION_KEY, description="Downloads graph-json")
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Rooms told of a rebuilt graph")
class CheckSourceAction(BaseAction[CheckSourceParams, CheckSourceResult]):
    """
    AI-CORE-BEGIN
    ROLE: One freshness check of one held source.
    CONTRACT: Unchanged → only the check time moves; changed → rebuilt and swapped on success, rooms told;
    unreachable or a failed build → the old graph stays. A check already running for the source → "skipped".
    INVARIANTS: Never two checks of one source at once; never a graph swapped before its build succeeded;
    the log names the source, never a participant.
    AI-CORE-END
    """

    @summary_aspect("Ask the service, rebuild a changed graph, tell the rooms")
    async def check_summary(
        self,
        params: CheckSourceParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> CheckSourceResult:
        """Check ``params.source`` once."""
        store = cast(GraphStoreController, connections[GRAPH_STORE_CONNECTION_KEY])
        gateway = cast(GraphSourceGateway, connections[GRAPH_SOURCE_CONNECTION_KEY])
        rooms = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        held = store.entry(params.source)
        if held is None:
            return CheckSourceResult(status="not_held")
        if store.is_checking(params.source):
            return CheckSourceResult(status="skipped", fingerprint=held.fingerprint)
        store.set_checking(params.source, True)
        try:
            status = await _check(params, held, store, gateway, rooms, box)
        finally:
            store.set_checking(params.source, False)
            store.mark_checked(params.source, store.now())
        current = store.entry(params.source)
        return CheckSourceResult(status=status, fingerprint=current.fingerprint if current else held.fingerprint)


async def _check(
    params: CheckSourceParams,
    held: GraphEntry,
    store: GraphStoreController,
    gateway: GraphSourceGateway,
    rooms: RoomRegistry,
    box: ToolsBox,
) -> CheckStatus:
    """Ask (unless forced), rebuild when changed, and say what happened."""
    if not params.force:
        answer = await gateway.fetch_if_changed(params.source, held.etag, held.last_modified)
        if isinstance(answer, Unreachable):
            await box.warning(Channel.error, "Source {%var.source} unreachable: {%var.reason}", source=label(params.source), reason=answer.reason)
            return "unreachable"
        if not isinstance(answer, Document) or answer.sha256 == held.content_sha256:
            await box.info(Channel.business, "Source {%var.source} unchanged", source=label(params.source))
            return "unchanged"
    try:
        rebuilt = await store.replace(params.source)
    except (GraphBuildError, GraphStoreBusyError) as exc:
        await box.warning(Channel.error, "Source {%var.source} not rebuilt: {%var.reason}", source=label(params.source), reason=str(exc))
        return "failed"
    if rebuilt.fingerprint != held.fingerprint:
        for room in rooms.rooms_of_source(params.source):
            rooms.broadcast(room, {"type": "graph_changed", "fingerprint": rebuilt.fingerprint})
    await box.info(Channel.business, "Source {%var.source} rebuilt", source=label(params.source))
    return "rebuilt"
