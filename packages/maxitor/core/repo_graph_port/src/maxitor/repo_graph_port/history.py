# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/history.py
"""
History — one graph file on one branch of one repository, named by an id.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

What a reader asks for when it asks for a history: where the graph file lives.
The histories config names each one; a public link names one without the config.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``HistoriesConfig.history(id)`` ──► ``History`` ──► the actions open its repository in the mirror.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class History:
    """
    AI-CORE-BEGIN
    ROLE: Where one history's graph file lives.
    CONTRACT: ``host`` is ``github`` or ``local``; ``repository`` is ``owner/name`` on the host, or a local path; ``branch`` gives the versions by first parent; ``graph_file`` is the file's path in the repository.
    AI-CORE-END
    """

    id: str
    host: str
    repository: str
    branch: str
    graph_file: str
