# packages/maxitor/front/src/maxitor/front/model/core/history_errors.py
"""
History refusals — the answers a history request can end in, each with its own words.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A history request is refused for one of a few reasons, and each has a fixed answer the
reader sees (spec 037, FR-009, FR-011e, the history routes' contract in specs/037). The words never name
a key or an address, so they are safe in a response body and in a log. The app turns
each into its status: not found ``404``, too many wrong keys ``429``, cannot be read now
``503``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    an aspect raises ──► the app's exception handler ──► {"detail": <the words>} with its status
"""

from __future__ import annotations


class HistoryNotFoundError(LookupError):
    """
    AI-CORE-BEGIN
    ROLE: The one answer for a wrong, revoked or expired key, an unknown history or a missing version.
    CONTRACT: The message is ``not found``; nothing tells the cases apart.
    AI-CORE-END
    """

    def __init__(self) -> None:
        super().__init__("not found")


class TooManyWrongKeysError(RuntimeError):
    """
    AI-CORE-BEGIN
    ROLE: The port blocked this Maxitor for too many wrong keys.
    CONTRACT: The message tells the reader to wait a minute; Maxitor does not retry on its own.
    AI-CORE-END
    """

    def __init__(self) -> None:
        super().__init__("Too many wrong keys for this history; try again in a minute")


class HistoryUnreachableError(RuntimeError):
    """
    AI-CORE-BEGIN
    ROLE: The port does not answer, or answers with an error of its own.
    CONTRACT: The message is the same whatever the cause; the cause goes to the log by the port's label only.
    AI-CORE-END
    """

    def __init__(self) -> None:
        super().__init__("The history cannot be read now.")
