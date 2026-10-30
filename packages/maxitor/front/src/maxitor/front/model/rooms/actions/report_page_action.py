# packages/maxitor/front/src/maxitor/front/model/rooms/actions/report_page_action.py
"""
ReportPageAction — a tab tells the room which page it shows and what it drew.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A tab reports its page on arrival, on every navigation and after every redraw, and
its visibility when it goes to the background (spec 028, FR-013, FR-044). Each report
marks the tab as the participant's active one. A report that carries what the tab
drew is checked (FR-090 … FR-093): the app build and the graph fingerprint against the
server's own values, the layout hash against the one the room takes as right for the
same page and settings — the followed person's, else the vote of the tabs there
(``layout_authority``, spec 038). The tab gets the verdict as ``check``; every other tab
whose layout verdict the report changed gets its new one; everyone else learns where the
participant is as ``presence``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "page", page, build, fingerprint, layout_hash, settings_digest}
    {"type": "activity", visible}
        └► tab: page, visibility, last activity
        └► check: build vs StaticBundle · fingerprint vs GraphStore · layout vs the room's right one
        └► recheck: every other tab whose layout verdict moved
        └► presence to the room
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from maxitor.front.model.core.resources.static_bundle_resource import (
    STATIC_BUNDLE_CONNECTION_KEY,
    StaticBundleResource,
)
from maxitor.front.model.rooms.actions.room_action_support import RoomAnswer, located
from maxitor.front.model.rooms.layout_authority import layout_verdict, recheck_layouts
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, Room, RoomRegistry, Tab
from maxitor.front.model.rooms.rooms_domain import RoomsDomain
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import SocketChannel


class ReportPageParams(BaseParams):
    """What the tab reports; every field is optional, so a visibility report carries only ``visible``."""

    page: str | None = Field(default=None, description="Canonical key of the page the tab shows")
    build: str | None = Field(default=None, description="The client build the tab runs")
    fingerprint: str | None = Field(default=None, description="Fingerprint of the graph the tab drew")
    layout_hash: str | None = Field(default=None, description="Layout hash of the picture the tab drew")
    settings_digest: str | None = Field(default=None, description="Digest of the page settings the picture used")
    layout_reloaded: bool | None = Field(default=None, description="Whether the tab reloaded for its layout lately")
    visible: bool | None = Field(default=None, description="Whether the tab is visible")


def _differs(reported: str | None, held: str) -> bool:
    """Whether the tab reported a value and the server holds a different one; a missing side never differs."""
    return bool(reported and held and reported != held)


def _verdict(params: ReportPageParams, tab: Tab, room: Room, server_build: str, held_fingerprint: str) -> dict[str, str]:
    """Compare what the tab drew with the server's build and graph, and its layout with the room's right one."""
    build = "reload" if _differs(params.build, server_build) else "ok"
    fingerprint = "reread" if _differs(params.fingerprint, held_fingerprint) else "ok"
    layout = layout_verdict(room, tab) if build == "ok" and fingerprint == "ok" else "ok"
    return {"build": build, "fingerprint": fingerprint, "layout": layout}


@meta(description="Record a tab's page and check what it drew", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The reporting tab's connection")
@connection(GraphStoreController, key=GRAPH_STORE_CONNECTION_KEY, description="Built graphs, for the fingerprint")
@connection(StaticBundleResource, key=STATIC_BUNDLE_CONNECTION_KEY, description="The client build Maxitor serves")
class ReportPageAction(BaseAction[ReportPageParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Keep a tab's page and visibility current, and judge whether its picture is the room's.
    CONTRACT: Build and fingerprint are compared with the server's values; the layout hash with the one the
    room takes as right for the same page and settings digest, and only when build and graph agree.
    INVARIANTS: Every report makes the tab the participant's active one; others are told by ``presence``.
    AI-CORE-END
    """

    @summary_aspect("Record the report, answer the check, tell the room")
    async def report_summary(
        self,
        params: ReportPageParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Update the tab, answer ``check`` when the report carries a picture, and announce presence."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        socket = cast(SocketChannel, connections["socket"])
        store = cast(GraphStoreController, connections[GRAPH_STORE_CONNECTION_KEY])
        bundle = cast(StaticBundleResource, connections[STATIC_BUNDLE_CONNECTION_KEY])
        room, participant, tab = located(registry, socket)
        async with room.lock:
            tab.last_activity = registry.clock()
            if params.visible is not None:
                tab.visible = params.visible
            if params.page is not None:
                arrived = params.page != tab.page
                tab.page = params.page
                tab.settings_digest = params.settings_digest or ""
                tab.build = params.build or ""
                tab.fingerprint = params.fingerprint or ""
                tab.layout_hash = params.layout_hash or ""
                tab.layout_reloaded = bool(params.layout_reloaded)
                if tab.layout_hash:
                    heard = room.layout_first_heard.setdefault((tab.page, tab.settings_digest), {})
                    heard.setdefault(tab.layout_hash, registry.clock())
                entry = store.entry(room.source)
                tab.check = _verdict(params, tab, room, bundle.build(), entry.fingerprint if entry else "")
                socket.send({"type": "check", **tab.check})
                recheck_layouts(room)
                if arrived:
                    registry.catch_up(room, tab, participant.id)
            registry.broadcast(room, {"type": "presence", **participant.public()}, except_participant=participant.id)
        return RoomAnswer()
