# packages/maxitor/src/maxitor/viewer/model/rooms/actions/seed_page_settings_action.py
"""
SeedPageSettingsAction — the person who opened a room brings their filters into it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A room shows one picture (spec 029, FR-001): right after the welcome of a room it
opened, the opener's tab sends its own values of every page setting, one per message.
Each value becomes the room's only where the room has none yet, so a change someone
made in the meantime wins. Only the room's creator may seed; a value the page does not
accept is skipped rather than refused, because it comes from a value kept in the
browser, not from a click.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "seed", "page", "settings": {name: value}} ──► the creator?
        └► for each value the room lacks and the page accepts:
               room.page_settings[page][name] = value ──► setting to the room
"""

from __future__ import annotations

from typing import Any, cast

from maxitor.viewer.model.rooms.actions.room_action_support import RoomAnswer, located
from maxitor.viewer.model.rooms.pages import setting_error
from maxitor.viewer.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from maxitor.viewer.model.rooms.rooms_domain import RoomsDomain
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseParams, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import SocketChannel


class SeedPageSettingsParams(BaseParams):
    """The page and the opener's own values for it."""

    page: str = Field(description="Canonical key of the page")
    settings: dict[str, Any] = Field(description="The opener's own value of each setting, by name")


@meta(description="Bring the opener's own page settings into the room they opened", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The opener's connection")
class SeedPageSettingsAction(BaseAction[SeedPageSettingsParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Make the room creator's own values of a page's settings the room's, where the room has none.
    CONTRACT: From anyone but the creator nothing changes and a security warning is logged; each applied value is announced as ``setting``.
    INVARIANTS: A value the room already holds is never overwritten; a value the page does not accept is skipped.
    AI-CORE-END
    """

    @summary_aspect("Apply the opener's values the room lacks and tell the room")
    async def seed_summary(
        self,
        params: SeedPageSettingsParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Store each missing, valid value and announce it."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        room, participant, _ = located(registry, cast(SocketChannel, connections["socket"]))
        if participant.id != room.created_by:
            await box.warning(
                Channel.security,
                "Seed refused in room {%var.room}: {%var.participant} did not open it",
                room=room.id,
                participant=participant.id,
            )
            return RoomAnswer()
        applied = 0
        async with room.lock:
            held = room.page_settings.setdefault(params.page, {})
            for name, value in params.settings.items():
                if name in held or setting_error(params.page, name, value):
                    continue
                held[name] = value
                applied += 1
                registry.broadcast(
                    room,
                    {"type": "setting", "page": params.page, "name": name, "value": value, "by": participant.id},
                )
        await box.info(
            Channel.business,
            "Room {%var.room} seeded with {%var.count} settings of a page",
            room=room.id,
            count=applied,
        )
        return RoomAnswer()
