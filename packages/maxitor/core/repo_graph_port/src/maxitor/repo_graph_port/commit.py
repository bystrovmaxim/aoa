# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/commit.py
"""
Commit — one commit of a branch, as git tells it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The facts of a commit that a version is made of: its ``sha``, its date and its
message. The mirror reads them; the history adds what the host knows.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``GitMirror.versions`` ──► ``Commit`` (date already in UTC) ──► a version of the history.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Commit:
    """
    AI-CORE-BEGIN
    ROLE: One commit: the identity, the date and the message of a version.
    CONTRACT: ``sha`` is the full hex id; ``date`` is the committer date in UTC, ``YYYY-MM-DDTHH:MM:SSZ``; ``message`` is the whole message, its trailing newline removed.
    AI-CORE-END
    """

    sha: str
    date: str
    message: str
