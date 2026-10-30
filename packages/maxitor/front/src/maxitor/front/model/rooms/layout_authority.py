# packages/maxitor/front/src/maxitor/front/model/rooms/layout_authority.py
"""
Layout authority — whose picture of a page the room takes as the right one.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pointers mean something only on the same picture, so the room compares the layout hash
every tab reports for a page and its settings (spec 028, FR-093). Whose hash is right is
decided anew on every change, from the people on the page now (spec 038):

- someone is followed there: the person followed is right — everyone goes after them;
- nobody is: the room votes — the hash most tabs drew wins, and a tie goes to the hash
  heard first most recently, which is the newest client after an update.

A tab whose picture is not the right one is told to reload once. If it still differs
after that, the right side may be the one on old code — a leader opened before an update —
so every tab drawing the right picture is told to reload once in turn. A tab that differs
once both sides reloaded is told ``off``: its pointers stay off.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    tabs on (page, settings) with a hash ──► followed person's? ──► their hash
                                         └─► otherwise ──► most tabs · newest on a tie
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from maxitor.front.model.rooms.resources.room_registry import Room, Tab


def tabs_drawing(room: Room, page: str, settings_digest: str) -> list[tuple[str, Tab]]:
    """Every tab that drew ``page`` with ``settings_digest``, with its participant's id."""
    return [
        (participant.id, tab)
        for participant in room.participants.values()
        for tab in participant.tabs.values()
        if tab.page == page and tab.settings_digest == settings_digest and tab.layout_hash and not tab.leaving
    ]


def layout_authority(room: Room, page: str, settings_digest: str, first_heard: Mapping[str, float]) -> str | None:
    """
    The hash the room takes as right for ``page`` and ``settings_digest``, or ``None`` when nobody drew it.

    ``first_heard`` maps each hash to when the room first heard it on this page.
    """
    drawing = tabs_drawing(room, page, settings_digest)
    if not drawing:
        return None
    followers = Counter(participant.follows for participant in room.participants.values() if participant.follows)
    led = [
        (room.participants[pid].follows is None, followers[pid], tab.last_activity, tab.layout_hash)
        for pid, tab in drawing
        if followers[pid]
    ]
    if led:
        return max(led)[3]
    votes = Counter(tab.layout_hash for _, tab in drawing)
    return max(votes, key=lambda layout: (votes[layout], first_heard.get(layout, 0.0)))


def layout_verdict(room: Room, tab: Tab) -> str:
    """
    ``reload`` for a tab whose picture is not the right one, ``off`` once it already reloaded; for a tab with the right
    picture, ``reload`` while another tab still differs after its own reload and this one has not reloaded yet;
    ``ok`` otherwise, and for a tab that drew nothing.
    """
    first_heard = room.layout_first_heard.get((tab.page, tab.settings_digest), {})
    authority = layout_authority(room, tab.page, tab.settings_digest, first_heard)
    if not tab.layout_hash or authority is None:
        return "ok"
    if tab.layout_hash != authority:
        return "off" if tab.layout_reloaded else "reload"
    drawing = tabs_drawing(room, tab.page, tab.settings_digest)
    stuck = any(other.layout_hash != authority and other.layout_reloaded for _, other in drawing)
    return "reload" if stuck and not tab.layout_reloaded else "ok"


def recheck_layouts(room: Room) -> None:
    """
    Tell every tab whose layout verdict changed — the right picture moved when someone came, went, reloaded or
    started or stopped following. Only a tab whose build and graph were right is judged by its layout.
    """
    for participant in room.participants.values():
        for tab in participant.tabs.values():
            if tab.check is None or tab.check["build"] != "ok" or tab.check["fingerprint"] != "ok":
                continue
            layout = layout_verdict(room, tab)
            if layout != tab.check["layout"]:
                tab.check = {**tab.check, "layout": layout}
                tab.channel.send({"type": "check", **tab.check})
