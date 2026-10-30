# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/contribution.py
"""
Contribution — who made a version and how large it was, as git tells it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A reader wants to know whose change a version is and how much it touched, in any
history — a local or corporate repository with no host to ask included. Git has
it: a merge commit's author is the person who merged; the commits it brought in
are the branch's, and their authors made the change; a squash or direct commit's
author made it. The size is the commit's diff against its first parent.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``GitMirror.contribution`` ──► ``Contribution`` ──► kept by ``VersionCache`` ──► ``VersionRecord``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Contribution(BaseModel):
    """Who made a version and how large it was."""

    model_config = ConfigDict(frozen=True)

    author: str = Field(description="Who made the change: the first author of a merged branch, or the commit's author")
    co_authors: int = Field(default=0, description="How many other people authored the merged branch's commits")
    merged_by: str | None = Field(default=None, description="Who merged it: a merge commit's author; None for a squash or direct commit")
    files: int = Field(default=0, description="Files the version changed against its first parent")
    additions: int = Field(default=0, description="Lines added")
    deletions: int = Field(default=0, description="Lines removed")
