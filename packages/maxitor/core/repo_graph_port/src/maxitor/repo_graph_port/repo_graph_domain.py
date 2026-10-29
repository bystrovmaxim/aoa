# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/repo_graph_domain.py
"""
RepoGraphDomain — the bounded context of reading a graph's history from its repository.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Declares the :class:`~aoa.action_machine.domain.base_domain.BaseDomain` subclass the
actions and resources of ``maxitor.repo_graph_port`` belong to, so its part of
Maxitor's own graph is one domain.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

A marker: ``@meta(domain=RepoGraphDomain)`` on every action and resource of the part.
"""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class RepoGraphDomain(BaseDomain):
    """
    AI-CORE-BEGIN
    ROLE: Marker domain for reading a graph's history from its repository.
    CONTRACT: ``name`` is ``repo_graph``; use with ``@meta(domain=RepoGraphDomain)``.
    INVARIANTS: Marker only — no I/O on the class.
    AI-CORE-END
    """

    name = "repo_graph"
    description = "A graph's history read from the repository that keeps its file: versions, tags, graphs"
