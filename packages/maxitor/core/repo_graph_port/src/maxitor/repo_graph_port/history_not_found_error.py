# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/history_not_found_error.py
"""
HistoryNotFoundError — what a reader asked for is not there, whatever the reason.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An unknown history, a version the history does not have, a ``sha`` that is not a
version — and, from the read keys on, a key that does not open the history — all
answer the same way, so a refusal tells a stranger nothing about what exists.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

action aspect ──raises──► ``HistoryNotFoundError`` ──the front's routes──► ``404 {"detail": "not found"}``.
"""

from __future__ import annotations


class HistoryNotFoundError(LookupError):
    """
    AI-CORE-BEGIN
    ROLE: The one refusal of every read: "not found".
    CONTRACT: The message is always ``not found``; why is never said.
    AI-CORE-END
    """

    def __init__(self) -> None:
        """Say "not found" and nothing more."""
        super().__init__("not found")
