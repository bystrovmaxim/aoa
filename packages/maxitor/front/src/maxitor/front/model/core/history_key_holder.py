# packages/maxitor/front/src/maxitor/front/model/core/history_key_holder.py
"""
HistoryKeyHolder — the reader of a history request, holding the read key it sent.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A private history opens only with its read key, which the browser sends in the header
``X-Maxitor-History-Key`` and nowhere else (spec 037, FR-010b). The history actions
need that key to pass it on to the port, so it travels in the request's context as the
reader's — never in params, which are logged and traced, and never in a representation.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    X-Maxitor-History-Key ──HistoryKeyAuthCoordinator──► Context(user=HistoryKeyHolder(history_key=…))
                                                              └──► ctx.get("user.history_key") in an aspect
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.context import UserInfo


class HistoryKeyHolder(UserInfo):
    """
    AI-CORE-BEGIN
    ROLE: Carry the read key a request sent, from the header to the history actions.
    CONTRACT: ``history_key`` is the header's value, ``""`` without one.
    INVARIANTS: The key is left out of ``repr`` and out of every serialised form.
    AI-CORE-END
    """

    history_key: str = Field(default="", repr=False, exclude=True, description="The read key the request sent; never shown")
