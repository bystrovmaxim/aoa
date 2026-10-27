# packages/aoa-maxitor/src/aoa/maxitor/model/rooms/resources/room_registry.py
"""
RoomRegistry — every open room of the process, as the resource room actions are given.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A room is state the process owns: who is in it, which tabs each person has open, the
shared settings of every page, who follows whom. That state lives here and nowhere
else, and actions reach it only through ``connections["RoomRegistry"]`` (spec 028,
research R1). The registry holds the state, delivers events, and starts timers; it
decides nothing. Whether a room is full, whether a name is valid, whether a follow
closes a circle, when a participant's return window ends — every such rule is an
aspect of a room action, which logs what it decided.

Two kinds of delivery exist. Events (someone joined, a setting changed) go to every
tab in order, through each tab's ``SocketChannel``. Pointers and screen positions are
relayed without an action, twenty times a second, only to the tabs on the same page,
and only the newest one counts (``send_volatile``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    room action ──connections["RoomRegistry"]──► RoomRegistry
                     │ rooms: id → Room (participants → tabs → SocketChannel)
                     │ broadcast(room, event)          ──► every tab, in order
                     │ schedule(delay, Action, params) ──► machine.run(Action) later
    adapter relay ──► relay(channel, pointer|viewport) ──► tabs on the same page, newest only
"""

from __future__ import annotations

import asyncio
import secrets
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from aoa.action_machine.context import Context
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import SocketChannel
from aoa.maxitor.model.rooms.rooms_domain import RoomsDomain

#: Connection key under which room actions receive the registry.
ROOM_REGISTRY_KEY = "RoomRegistry"

#: Participant colours, told apart on light and dark backgrounds; a participant gets the first free one.
PALETTE: tuple[str, ...] = (
    "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#4f46e5",
    "#ea580c", "#059669", "#a855f7", "#0d9488", "#e11d48", "#65a30d", "#c026d3", "#0369a1",
    "#b45309", "#15803d", "#9333ea", "#be185d",
)

#: The relayed message types and the numeric fields each one may carry.
_RELAYED_FIELDS: dict[str, tuple[str, ...]] = {
    "pointer": ("x", "y"),
    "viewport": ("cx", "cy", "w", "h"),
}


@dataclass
class Tab:
    """One browser tab of a participant: its connection, its page, and what it last reported."""

    id: str
    channel: SocketChannel
    page: str
    last_activity: float
    visible: bool = True
    build: str = ""
    fingerprint: str = ""
    layout_hash: str = ""
    settings_digest: str = ""
    pointer: dict[str, Any] | None = None
    viewport: dict[str, Any] | None = None
    leaving: bool = False


@dataclass
class Participant:
    """One person in a room, across all the tabs of one browser."""

    id: str
    name: str
    colour: int
    tabs: dict[str, Tab] = field(default_factory=dict)
    follows: str | None = None
    return_until: float | None = None

    @property
    def active_tab(self) -> Tab | None:
        """The tab the participant used last; the only one whose page and pointer others see."""
        return max(self.tabs.values(), key=lambda tab: tab.last_activity, default=None)

    @property
    def away(self) -> bool:
        """Whether the participant lost every connection and may still come back."""
        return not self.tabs and self.return_until is not None

    def public(self) -> dict[str, Any]:
        """What other participants are told about this one."""
        active = self.active_tab
        return {
            "id": self.id,
            "name": self.name,
            "colour": PALETTE[self.colour % len(PALETTE)],
            "page": active.page if active else None,
            "visible": active.visible if active else False,
            "away": self.away,
        }


@dataclass
class Room:
    """One room: its source, its participants, and the shared settings of every page."""

    id: str
    source: str
    created_by: str
    participants: dict[str, Participant] = field(default_factory=dict)
    page_settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    reported_hashes: dict[tuple[str, str], str] = field(default_factory=dict)
    empty_since: float | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def follows(self) -> dict[str, str | None]:
        """Who follows whom, for every participant."""
        return {pid: participant.follows for pid, participant in self.participants.items()}

    def snapshot(self) -> dict[str, Any]:
        """The whole room as a newcomer is told it."""
        return {
            "id": self.id,
            "source": self.source,
            "created_by": self.created_by,
            "participants": [participant.public() for participant in self.participants.values()],
            "settings": self.page_settings,
            "follows": self.follows(),
        }


def _is_number(value: Any) -> bool:
    """Whether ``value`` is a JSON number (a bool is not one)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _tabs_on_page(room: Room, page: str, *, except_participant: str) -> list[Tab]:
    """The tabs of ``room`` that show ``page``, other than ``except_participant``'s."""
    return [
        tab
        for participant in room.participants.values()
        if participant.id != except_participant
        for tab in participant.tabs.values()
        if tab.page == page
    ]


@meta(description="Every open room of the process: participants, tabs, shared settings", domain=RoomsDomain)
class RoomRegistry(BaseController):
    """
    AI-CORE-BEGIN
    ROLE: The resource that holds every open room and delivers its events to the tabs in it.
    CONTRACT: State changes happen through the small helpers below, called by room actions under the
    room's ``lock``; ``relay`` sends pointers and screen positions only to tabs on the sender's page.
    INVARIANTS: Decides nothing — limits, names, circles and timing are checked in actions; an ended
    room id is remembered and never reused; colours are unique within a room.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        return_window_seconds: float = 120.0,
        empty_room_seconds: float = 120.0,
        allowed_origins: tuple[str, ...] = (),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.return_window_seconds = return_window_seconds
        self.empty_room_seconds = empty_room_seconds
        self.allowed_origins = allowed_origins
        self.clock = clock
        self._rooms: dict[str, Room] = {}
        self._ended: set[str] = set()
        self._by_channel: dict[str, tuple[str, str, str]] = {}
        self._machine: ActionProductMachine | None = None
        self._timers: set[asyncio.Task[None]] = set()

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions use this same registry."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the in-memory registry is not a rollup target."""
        return False

    def bind(self, machine: ActionProductMachine) -> None:
        """Give the registry the machine its timers run actions on."""
        self._machine = machine

    # ── rooms ───────────────────────────────────────────────────────────

    def room(self, room_id: str) -> Room | None:
        """The open room with ``room_id``, or ``None``."""
        return self._rooms.get(room_id)

    def has_ended(self, room_id: str) -> bool:
        """Whether a room with ``room_id`` existed and ended."""
        return room_id in self._ended

    def room_count(self) -> int:
        """How many rooms are open."""
        return len(self._rooms)

    def rooms_of_source(self, source: str) -> Iterator[Room]:
        """Every open room of ``source``."""
        return (room for room in self._rooms.values() if room.source == source)

    def open_room(self, source: str, created_by: str) -> Room:
        """Create a room with a fresh 128-bit id."""
        room_id = secrets.token_urlsafe(16)
        while room_id in self._rooms or room_id in self._ended:
            room_id = secrets.token_urlsafe(16)
        room = Room(id=room_id, source=source, created_by=created_by)
        self._rooms[room_id] = room
        return room

    def end_room(self, room: Room) -> None:
        """Remove ``room`` for good; its id is never reused."""
        self._rooms.pop(room.id, None)
        self._ended.add(room.id)

    # ── participants and tabs ────────────────────────────────────────────

    def free_colour(self, room: Room) -> int:
        """The first palette index no participant of ``room`` has."""
        taken = {participant.colour for participant in room.participants.values()}
        return next(index for index in range(len(PALETTE) + len(taken) + 1) if index not in taken)

    def add_participant(self, room: Room, participant_id: str, name: str) -> Participant:
        """Add a new participant with the first free colour."""
        participant = Participant(id=participant_id, name=name.strip(), colour=self.free_colour(room))
        room.participants[participant_id] = participant
        return participant

    def remove_participant(self, room: Room, participant_id: str) -> Participant | None:
        """Remove a participant and everyone's link to them; close their tabs."""
        participant = room.participants.pop(participant_id, None)
        if participant is None:
            return None
        for other in room.participants.values():
            if other.follows == participant_id:
                other.follows = None
        for tab in participant.tabs.values():
            tab.leaving = True
            self._by_channel.pop(tab.channel.id, None)
            tab.channel.close(1000, "left the room")
        participant.tabs.clear()
        return participant

    def add_tab(self, room: Room, participant: Participant, tab_id: str, channel: SocketChannel, page: str) -> Tab:
        """Attach a tab (a connection) to ``participant``."""
        tab = Tab(id=tab_id, channel=channel, page=page, last_activity=self.clock())
        participant.tabs[tab_id] = tab
        self._by_channel[channel.id] = (room.id, participant.id, tab_id)
        return tab

    def remove_tab(self, participant: Participant, tab_id: str) -> Tab | None:
        """Detach a tab from ``participant``."""
        tab = participant.tabs.pop(tab_id, None)
        if tab is not None:
            self._by_channel.pop(tab.channel.id, None)
        return tab

    def locate(self, channel: SocketChannel) -> tuple[Room, Participant, Tab] | None:
        """The room, participant and tab a connection belongs to."""
        found = self._by_channel.get(channel.id)
        if found is None:
            return None
        room = self._rooms.get(found[0])
        participant = room.participants.get(found[1]) if room else None
        tab = participant.tabs.get(found[2]) if participant else None
        if room is None or participant is None or tab is None:
            return None
        return room, participant, tab

    # ── delivery ─────────────────────────────────────────────────────────

    def broadcast(self, room: Room, event: Mapping[str, Any], *, except_participant: str | None = None) -> None:
        """Send ``event`` to every tab of every participant of ``room``, except one participant's."""
        for participant in room.participants.values():
            if participant.id == except_participant:
                continue
            for tab in participant.tabs.values():
                tab.channel.send(event)

    def relay(self, channel: SocketChannel, message: dict[str, Any]) -> None:
        """Pass a pointer or screen position on to the other participants' tabs on the sender's page."""
        found = self.locate(channel)
        kind = message.get("type")
        fields = _RELAYED_FIELDS.get(str(kind))
        if found is None or fields is None:
            return
        room, sender, tab = found
        values = {name: message.get(name) for name in fields}
        if not all(_is_number(value) for value in values.values()):
            return
        tab.last_activity = self.clock()
        if kind == "pointer":
            values["kind"] = "touch" if message.get("kind") == "touch" else "mouse"
            tab.pointer = values
        else:
            tab.viewport = values
        event = {"type": kind, "participant": sender.id, **values}
        for other in _tabs_on_page(room, tab.page, except_participant=sender.id):
            other.channel.send_volatile(f"{kind}:{sender.id}", event)

    def catch_up(self, room: Room, tab: Tab, participant: str) -> None:
        """
        Give a tab that just arrived on a page where the others are: each one's last screen, and their
        mouse pointer however long it has stood still, since a pointer shows for as long as its person is
        in the room (spec 029, FR-021); a tap is a moment and is never brought. Volatile, like the relay,
        and never logged.
        """
        for other in room.participants.values():
            active = other.active_tab
            if other.id == participant or active is None or active.page != tab.page:
                continue
            if active.viewport is not None:
                tab.channel.send_volatile(f"viewport:{other.id}", {"type": "viewport", "participant": other.id, **active.viewport})
            pointer = active.pointer
            if pointer is not None and pointer.get("kind") == "mouse":
                tab.channel.send_volatile(f"pointer:{other.id}", {"type": "pointer", "participant": other.id, **pointer})

    # ── timers ───────────────────────────────────────────────────────────

    def schedule(self, delay: float, action_class: type[BaseAction[Any, Any]], params: BaseParams) -> None:
        """Run ``action_class`` with ``params`` through the machine after ``delay`` seconds."""
        machine = self._machine
        if machine is None:
            raise RuntimeError("RoomRegistry.bind(machine) was not called")

        async def later() -> None:
            await asyncio.sleep(delay)
            await machine.run(Context(), action_class(), params, {ROOM_REGISTRY_KEY: self})

        task = asyncio.create_task(later())
        self._timers.add(task)
        task.add_done_callback(self._timers.discard)

    async def close(self) -> None:
        """Cancel the timers that have not fired yet."""
        for task in list(self._timers):
            task.cancel()
        self._timers.clear()
