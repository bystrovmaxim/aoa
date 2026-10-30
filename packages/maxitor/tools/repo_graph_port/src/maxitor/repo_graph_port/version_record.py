# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/version_record.py
"""
VersionRecord — one version as a history lists it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Everything a reader needs to pick a version without reading its graph: when, why
(the pull request or the commit message), which tags, how large, and whether the
file is a graph at all.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``Commit`` + placed tags + ``GraphFacts`` ──► ``VersionRecord`` ──► ``HistoryAction``'s answer.
"""

from __future__ import annotations

from maxitor.repo_graph_port.contribution import Contribution
from maxitor.repo_graph_port.placed_tag import PlacedTag
from pydantic import BaseModel, ConfigDict, Field


class VersionRecord(BaseModel):
    """One version of a history."""

    model_config = ConfigDict(frozen=True)

    sha: str = Field(description="The commit, by first parent, that changed the graph file")
    date: str = Field(description="The commit's date, UTC, ISO 8601")
    pr: dict[str, str | int] | None = Field(default=None, description="The pull request: number, title, body, url")
    message: str | None = Field(default=None, description="The commit's message, when there is no pull request")
    tags: list[PlacedTag] = Field(default_factory=list, description="The repository's tags placed on this version")
    nodes: int | None = Field(default=None, description="Nodes of its graph")
    edges: int | None = Field(default=None, description="Edges of its graph")
    refused: str | None = Field(default=None, description="Why its file is not a graph")
    contribution: Contribution | None = Field(default=None, description="Who made it and how large it was, from git")
    change: dict[str, object] | None = Field(default=None, description="What it did to the previous version's graph: nodes added and removed by kind, nodes changed, links added and removed")
