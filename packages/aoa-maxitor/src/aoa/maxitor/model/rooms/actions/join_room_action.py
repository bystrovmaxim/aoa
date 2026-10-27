# packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/join_room_action.py
"""
JoinRoomAction — a tab opens a room, or joins one, when its connection opens.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Runs once per connection, as the WebSocket route's open action. ``room_id = "new"``
opens a room for ``source`` (spec 028, FR-010); any other id joins that room. The
action decides who may come in and logs it: the ``Origin`` must be Maxitor's own
(FR-016), the name 1–40 characters (FR-011), a room holds 20 people and a process 100
rooms (FR-015). Someone coming back within two minutes keeps their place and colour
and nobody is told they left (FR-062). A page the room's service does not offer is
replaced by the page of the person who opened the room, or of whoever was active last
(FR-010). The newcomer gets ``welcome`` with the whole room; everyone else gets
``joined`` or ``presence``. The log names rooms and participants by id only (FR-069).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    connect ?participant&tab&participant_name&start_page[&source]
        └► origin? name? ──► room new | existing (ended → 4404) ──► full? (4409)
               └► GraphStore.acquire(source) → pages → start page or fallback
                      └► registry.add_tab ──► welcome to the tab; joined / presence to the room
"""

from __future__ import annotations

from typing import cast

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
from aoa.maxitor.api.graph_store import GraphBuildError, GraphEntry, GraphStoreBusyError
from aoa.maxitor.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from aoa.maxitor.model.core.resources.static_bundle_resource import STATIC_BUNDLE_CONNECTION_KEY, StaticBundleResource
from aoa.maxitor.model.rooms.actions.room_action_support import (
    INVALID_VALUE,
    MAX_PARTICIPANTS,
    MAX_ROOMS,
    ORIGIN_NOT_ALLOWED,
    ROOM_ENDED,
    ROOM_FULL,
    SOURCE_UNAVAILABLE,
    TOO_MANY_ROOMS,
    RoomAnswer,
    origin_allowed,
)
from aoa.maxitor.model.rooms.pages import name_error, page_key, page_keys
from aoa.maxitor.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, Room, RoomRegistry
from aoa.maxitor.model.rooms.rooms_domain import RoomsDomain

#: The room id a connection uses to open a new room.
NEW_ROOM = "new"


class JoinRoomParams(BaseParams):
    """The connection's values: path, query and headers."""

    room_id: str = Field(min_length=1, description="The room to join, or 'new' to open one")
    participant: str = Field(min_length=1, max_length=64, description="Participant id kept by the browser per room")
    tab: str = Field(min_length=1, max_length=64, description="Tab id kept by the browser per tab")
    participant_name: str = Field(description="The name the person typed")
    start_page: str = Field(description="Canonical key of the page the tab opens on")
    source: str = Field(default="", description="The service a new room is for; ignored when joining")
    origin: str = Field(default="", description="The connection's Origin header")
    host: str = Field(default="", description="The connection's Host header")


def _fallback_page(room: Room, pages: set[str]) -> str:
    """The page a newcomer opens when theirs does not exist: the creator's, else the last active, else the full graph."""
    creator = room.participants.get(room.created_by)
    candidates = [creator] if creator else []
    candidates += sorted(
        room.participants.values(),
        key=lambda participant: participant.active_tab.last_activity if participant.active_tab else 0.0,
        reverse=True,
    )
    for participant in candidates:
        active = participant.active_tab if participant else None
        if active and active.page in pages:
            return active.page
    full_graph = page_key("full-graph")
    return full_graph if full_graph in pages or not pages else sorted(pages)[0]


@meta(description="Open a room or join one when a connection opens", domain=RoomsDomain)
@check_roles(GuestRole)
@connection(RoomRegistry, key=ROOM_REGISTRY_KEY, description="Every open room")
@connection(SocketChannel, key="socket", description="The joining tab's connection")
@connection(GraphStoreController, key=GRAPH_STORE_CONNECTION_KEY, description="Built graphs, for the room's pages")
@connection(StaticBundleResource, key=STATIC_BUNDLE_CONNECTION_KEY, description="The client build Maxitor serves")
class JoinRoomAction(BaseAction[JoinRoomParams, RoomAnswer]):
    """
    AI-CORE-BEGIN
    ROLE: Decide whether a connecting tab may open or join a room, and seat it there.
    CONTRACT: Refuses with 4403 (origin), 4422 (name or missing source), 4503 (too many rooms), 4404 (room
    ended or unknown), 4409 (room full); otherwise sends ``welcome`` and tells the room.
    INVARIANTS: A returning participant keeps id and colour and is not announced as joined; the log
    carries ids, never names.
    AI-CORE-END
    """

    @summary_aspect("Check the newcomer, seat the tab and tell the room")
    async def join_summary(
        self,
        params: JoinRoomParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> RoomAnswer:
        """Refuse or seat the connecting tab."""
        registry = cast(RoomRegistry, connections[ROOM_REGISTRY_KEY])
        socket = cast(SocketChannel, connections["socket"])
        store = cast(GraphStoreController, connections[GRAPH_STORE_CONNECTION_KEY])
        bundle = cast(StaticBundleResource, connections[STATIC_BUNDLE_CONNECTION_KEY])

        if not origin_allowed(params.origin, params.host, registry.allowed_origins):
            await box.warning(Channel.security, "Room join refused: foreign origin {%var.origin}", origin=params.origin)
            raise ConnectionRefusalError(ORIGIN_NOT_ALLOWED, "origin not allowed")
        if name_error(params.participant_name):
            await box.warning(Channel.security, "Room join refused: invalid name for {%var.room}", room=params.room_id)
            raise ConnectionRefusalError(INVALID_VALUE, "invalid name")

        room, entry = await self._room(params, registry, store, box)
        pages = page_keys(entry.sidebar)

        async with room.lock:
            participant = room.participants.get(params.participant)
            returning = participant is not None
            if participant is None:
                if len(room.participants) >= MAX_PARTICIPANTS:
                    await box.warning(Channel.security, "Room join refused: {%var.room} is full", room=room.id)
                    raise ConnectionRefusalError(ROOM_FULL, "room full")
                participant = registry.add_participant(room, params.participant, params.participant_name)
            was_away = participant.away
            participant.return_until = None
            fallback = None if params.start_page in pages else _fallback_page(room, pages)
            registry.add_tab(room, participant, params.tab, socket, fallback or params.start_page)
            room.empty_since = None
            socket.send(
                {
                    "type": "welcome",
                    "you": {"id": participant.id, "colour": participant.public()["colour"]},
                    "room": room.snapshot(),
                    "server_build": bundle.build(),
                    "fallback_page": fallback,
                }
            )
            if not returning:
                registry.broadcast(room, {"type": "joined", "participant": participant.public()}, except_participant=participant.id)
            else:
                registry.broadcast(room, {"type": "presence", **participant.public()}, except_participant=participant.id)

        if not returning:
            await box.info(Channel.business, "Participant {%var.participant} joined room {%var.room}", participant=participant.id, room=room.id)
        elif was_away:
            await box.info(Channel.business, "Participant {%var.participant} returned to room {%var.room}", participant=participant.id, room=room.id)
        return RoomAnswer()

    @staticmethod
    async def _room(
        params: JoinRoomParams,
        registry: RoomRegistry,
        store: GraphStoreController,
        box: ToolsBox,
    ) -> tuple[Room, GraphEntry]:
        """Find the named room or open a new one once its source is built; refuse what cannot be."""
        if params.room_id != NEW_ROOM:
            existing = registry.room(params.room_id)
            if existing is None:
                await box.warning(Channel.security, "Room join refused: {%var.room} has ended", room=params.room_id)
                raise ConnectionRefusalError(ROOM_ENDED, "room ended")
            return existing, await _built(store, existing.source)
        if not params.source:
            raise ConnectionRefusalError(INVALID_VALUE, "a new room needs a source")
        if registry.room_count() >= MAX_ROOMS:
            await box.warning(Channel.security, "Room creation refused: {%var.limit} rooms are open", limit=MAX_ROOMS)
            raise ConnectionRefusalError(TOO_MANY_ROOMS, "too many rooms")
        entry = await _built(store, params.source)
        room = registry.open_room(params.source, params.participant)
        await box.info(Channel.business, "Room {%var.room} created for {%var.source}", room=room.id, source=params.source)
        return room, entry


async def _built(store: GraphStoreController, source: str) -> GraphEntry:
    """The built graph of ``source``; refuse the connection when it cannot be built now."""
    try:
        return await store.acquire(source)
    except (GraphBuildError, GraphStoreBusyError) as exc:
        raise ConnectionRefusalError(SOURCE_UNAVAILABLE, "the service's graph cannot be built now") from exc
