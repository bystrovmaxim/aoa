# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/too_many_wrong_keys_error.py
"""
TooManyWrongKeysError — one client sent too many keys that open nothing.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Guessing a key is slowed down: after a set number of wrong keys from one client
address in a minute, every request from it is refused until the minute passes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``HistoryKeyAuthCoordinator`` ──raises──► ``TooManyWrongKeysError`` ──the port's server──► ``429``.
"""

from __future__ import annotations


class TooManyWrongKeysError(RuntimeError):
    """
    AI-CORE-BEGIN
    ROLE: The refusal of a client that sent too many wrong keys.
    CONTRACT: The message is ``too many requests``; it names neither the client nor a key.
    AI-CORE-END
    """

    def __init__(self) -> None:
        """Say "too many requests" and nothing more."""
        super().__init__("too many requests")
