# packages/maxitor/tools/repo-graph-port/maxitor/repo_graph_port/history.py
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
from collections.abc import Sequence
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class History:
    """
    AI-CORE-BEGIN
    ROLE: Where one history's graph file lives.
    CONTRACT: ``host`` is ``github`` or ``local``; ``repository`` is ``owner/name`` on the host, or a local path; ``branch`` gives the versions by first parent; ``graph_file`` is the file's path in the repository; ``public`` is true for a history named by a link, read with no key and no credentials; ``live`` is the address of the running service whose graph is Live, or ``None``.
    AI-CORE-END
    """

    id: str
    host: str
    repository: str
    branch: str
    graph_file: str
    public: bool = False
    live: str | None = None
    version_file: str | None = None
    version_key: str = "version"
    graph_file_before: tuple[str, ...] = ()
    version_file_before: tuple[str, ...] = ()
    version_refused: str | None = None

    @property
    def graph_paths(self) -> tuple[str, ...]:
        """The graph file's paths, newest first."""
        return (self.graph_file, *self.graph_file_before)

    @property
    def version_paths(self) -> tuple[str, ...]:
        """The version file's paths, newest first; none without a version file."""
        return (self.version_file, *self.version_file_before) if self.version_file else ()

    @property
    def watched_paths(self) -> tuple[str, ...]:
        """Every path whose change can make a point."""
        return (*self.graph_paths, *self.version_paths)

    def followed(self, graph_before: Sequence[str], version_before: Sequence[str]) -> History:
        """The history with the earlier paths git found joined to the ones its config lists, newest first, none twice."""
        return replace(
            self,
            graph_file_before=_joined(graph_before, self.graph_file_before, self.graph_file),
            version_file_before=_joined(version_before, self.version_file_before, self.version_file),
        )


def _joined(found: Sequence[str], listed: Sequence[str], current: str | None) -> tuple[str, ...]:
    """``found`` then ``listed``, each path once, the current path left out."""
    return tuple(dict.fromkeys(path for path in (*found, *listed) if path != current))


def _blob(link: str) -> tuple[str, str, str, str] | None:
    """The owner, repository, branch and path of a link to a public file."""
    found = re.fullmatch(r"https://github\.com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)/blob/([A-Za-z0-9._-]+)/([^?#]+)", link)
    if found is None or ".." in found.group(4).split("/"):
        return None
    owner, name, branch, path = found.groups()
    return owner, name, branch, path


def public_history(link: str, version_link: str | None = None, version_key: str | None = None) -> History | None:
    """
    AI-CORE-BEGIN
    ROLE: Name a public history by a link to its graph file.
    CONTRACT: ``https://github.com/<owner>/<repo>/blob/<branch>/<path>`` gives a public ``History`` whose id is the link; anything else gives ``None``. ``version_link`` names the version file the same way; one that is not a file of the same repository and branch sets ``version_refused``. A branch with a slash in its name is not recognised.
    AI-CORE-END
    """
    blob = _blob(link)
    if blob is None:
        return None
    owner, name, branch, path = blob
    history = History(id=link, host="github", repository=f"{owner}/{name}", branch=branch, graph_file=path, public=True)
    if version_link is None:
        return history
    version = _blob(version_link)
    if version is None or version[:3] != blob[:3]:
        return replace(history, version_refused=f"the version link is not a file of {owner}/{name} on {branch}")
    return replace(history, version_file=version[3], version_key=version_key or "version")
