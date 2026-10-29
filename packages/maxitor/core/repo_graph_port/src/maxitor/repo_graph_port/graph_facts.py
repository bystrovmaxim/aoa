# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/graph_facts.py
"""
GraphFacts — what a version's graph file says about itself.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A version lists the size of its graph, or why its file is not a graph. Both come
from the file's bytes alone, so they never change for a commit.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

the file's bytes ──► ``graph_facts`` ──► ``GraphFacts`` — counts, or the refusal.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphFacts:
    """
    AI-CORE-BEGIN
    ROLE: The counts of a version's graph, or the reason it is not a graph.
    CONTRACT: A graph has ``nodes`` and ``edges`` and ``refused`` is ``None``; a refused file has ``refused`` and no counts.
    AI-CORE-END
    """

    nodes: int | None
    edges: int | None
    refused: str | None
