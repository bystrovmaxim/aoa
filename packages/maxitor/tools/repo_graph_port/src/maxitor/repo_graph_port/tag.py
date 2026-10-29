# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/tag.py
"""
Tag — one tag of a repository and the commit it marks.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A repository's tags mark releases. A history shows each on the version it belongs
to, so a tag is its name and the commit it points at — an annotated tag already
followed to its commit.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``GitMirror.tags`` ──► ``Tag`` ──► ``place_tags`` ──► the version it lands on.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tag:
    """
    AI-CORE-BEGIN
    ROLE: One tag: its name and the commit it marks.
    CONTRACT: ``name`` is the short name (``v1.0``); ``sha`` is the commit, never the tag object.
    AI-CORE-END
    """

    name: str
    sha: str
