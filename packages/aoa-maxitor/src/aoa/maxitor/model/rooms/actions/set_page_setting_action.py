# packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/set_page_setting_action.py
"""
SetPageSettingAction — someone changes a filter or a layout mode of a page in the room.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every page's filters and layout mode belong to the room (spec 028, FR-030). A change
is a value, never a toggle, so two people clicking at once end in the last value
whatever order the messages arrive in (FR-031). A setting the page does not have, or
a value it does not accept, is refused with the reason.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    {"type": "setting", "page", "name", "value"} ──► known? fits?
        └► room.page_settings[page][name] = value ──► setting to the room
"""

from __future__ import annotations

from typing import Any, cast

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
from aoa.fastapi import ConnectionRefusalError, SocketChannel
from aoa.maxitor.model.rooms.actions.room_action_support import INVALID_VALUE, RoomAnswer, located
from aoa.maxitor.model.rooms.pages import setting_error
from aoa.maxitor.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from aoa.maxitor.model.rooms.rooms_domain import RoomsDomain


class SetPageSettingParams(BaseParams):
    """Which setting of which page, and its new value."""

    page: str = Field(description="Canonical key of the page")
    name: str = Field(description="The setting's name")
    value: Any = Field(description="The setting's new value: a word, a boolean or a list of names")


@meta(description="Change a shared filter or layout mode of a page", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The participant's connection")
class SetPageSettingAction(BaseAction[SetPageSettingParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Set one shared setting of one page of the room and tell everyone.
    CONTRACT: Refuses an unknown page, setting or value with 4422 and the reason; the last value wins.
    INVARIANTS: Values are stored as given, never toggled.
    AI-CORE-END
    """

    @summary_aspect("Validate the setting and tell the room")
    async def setting_summary(
        self,
        params: SetPageSettingParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Store the value and announce it."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        room, participant, _ = located(registry, cast(SocketChannel, connections["socket"]))
        error = setting_error(params.page, params.name, params.value)
        if error:
            raise ConnectionRefusalError(INVALID_VALUE, error)
        async with room.lock:
            room.page_settings.setdefault(params.page, {})[params.name] = params.value
            registry.broadcast(
                room,
                {"type": "setting", "page": params.page, "name": params.name, "value": params.value, "by": participant.id},
            )
        await box.info(
            Channel.business,
            "Setting {%var.setting} changed in room {%var.room}",
            setting=params.name,
            room=room.id,
        )
        return RoomAnswer()
