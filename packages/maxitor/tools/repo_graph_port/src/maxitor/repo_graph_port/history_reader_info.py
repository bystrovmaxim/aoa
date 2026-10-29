# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/history_reader_info.py
"""
HistoryReaderInfo — who reads, and which configured history their key opens.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The identity a request carries into the actions: the key's name as the user, and
the one history the key opens. A reader without a key carries no history and can
read only public links.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

coordinator ──► ``HistoryReaderInfo`` ──``@context_requires("user.history")``──► the action compares it with the history asked for.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.context import UserInfo


class HistoryReaderInfo(UserInfo):
    """
    AI-CORE-BEGIN
    ROLE: The reader's identity: the key's name and the history it opens.
    CONTRACT: ``user_id`` is the key's ``name``; ``history`` is the id the key opens, ``""`` without a key.
    INVARIANTS: Never holds the key or its hash.
    AI-CORE-END
    """

    history: str = Field(default="", description="The id of the one configured history the reader's key opens")
