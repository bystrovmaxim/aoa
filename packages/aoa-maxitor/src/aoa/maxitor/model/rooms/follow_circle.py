# packages/aoa-maxitor/src/aoa/maxitor/model/rooms/follow_circle.py
"""
Follow circles — the rule that following someone may never close a circle.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When Boris follows Anna, Boris's screen goes wherever Anna's goes. If Anna then
followed Boris, the two screens would chase each other forever; the same happens
through any number of people. ``would_close_circle`` answers whether a new link
"follower → target" would create such a circle, so the follow action can refuse it
(spec 028, FR-054). The client uses the same rule to disable the button; the
server's answer, under the room's lock, is the one that counts.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    follows = {"vera": "anna", "anna": "boris"}      # who follows whom
    would_close_circle(follows, "boris", "vera")     # boris → vera → anna → boris : True
"""

from __future__ import annotations

from collections.abc import Mapping


def would_close_circle(follows: Mapping[str, str | None], follower: str, target: str) -> bool:
    """Whether ``follower`` following ``target`` closes a circle: ``target``'s own links lead back to ``follower``."""
    seen: set[str] = set()
    current: str | None = target
    while current is not None and current not in seen:
        if current == follower:
            return True
        seen.add(current)
        current = follows.get(current)
    return False
