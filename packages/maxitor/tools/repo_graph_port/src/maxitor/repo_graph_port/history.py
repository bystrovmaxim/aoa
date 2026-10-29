# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/history.py
"""
History — one graph file on one branch of one repository, named by an id.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

What a reader asks for when it asks for a history: where the graph file lives.
The histories config names each one; a public link names one without the config,
through ``public_history``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``HistoriesConfig.history(id)`` or ``public_history(link)`` ──► ``History`` ──► the actions open its repository in the mirror.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class History:
    """
    AI-CORE-BEGIN
    ROLE: Where one history's graph file lives.
    CONTRACT: ``host`` is ``github`` or ``local``; ``repository`` is ``owner/name`` on the host, or a local path; ``branch`` gives the versions by first parent; ``graph_file`` is the file's path in the repository; ``public`` is true for a history named by a link, read with no key and no credentials.
    AI-CORE-END
    """

    id: str
    host: str
    repository: str
    branch: str
    graph_file: str
    public: bool = False


def public_history(link: str) -> History | None:
    """
    AI-CORE-BEGIN
    ROLE: Name a public history by a link to its graph file.
    CONTRACT: ``https://github.com/<owner>/<repo>/blob/<branch>/<path>`` gives a public ``History`` whose id is the link; anything else gives ``None``. A branch with a slash in its name is not recognised.
    AI-CORE-END
    """
    found = re.fullmatch(r"https://github\.com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)/blob/([A-Za-z0-9._-]+)/([^?#]+)", link)
    if found is None or ".." in found.group(4).split("/"):
        return None
    owner, name, branch, path = found.groups()
    return History(id=link, host="github", repository=f"{owner}/{name}", branch=branch, graph_file=path, public=True)
