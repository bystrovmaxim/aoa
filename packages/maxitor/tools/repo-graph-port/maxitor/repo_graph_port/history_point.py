# packages/maxitor/tools/repo-graph-port/maxitor/repo_graph_port/history_point.py
"""
HistoryPoint — one point of a history: a commit, and what it changed.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A history joins two files, so a commit may change the graph, the version or both.
A point says which, and which commit's graph is in force at it, so a point that
changed only the version reads no graph.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``points_of`` ──► ``HistoryPoint`` ──► ``VersionRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass

from maxitor.repo_graph_port.commit import Commit


@dataclass(frozen=True)
class HistoryPoint:
    """A commit of a history, and what it changed."""

    commit: Commit
    graph_at: str
    before: str | None
    graph_changed: bool = True
    version: str | None = None
    version_changed: bool = False
