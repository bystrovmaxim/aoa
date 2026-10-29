# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/resources/histories_config.py
"""
HistoriesConfig — the histories a server serves, from its config file.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The file named by ``MAXITOR_HISTORIES`` lists each history a server serves: an id,
the host, the repository, the branch and the graph file's path. An action asks
for a history by id and learns where its file lives, or that there is none.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    TOML ``[[history]]`` ──load──► {id: History} ──history(id)──► History | None

A file that is not valid TOML, a history missing a field, an unknown host or an
id given twice refuses the whole file with a ``ValueError`` naming what is wrong.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from maxitor.repo_graph_port.history import History
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


@meta(description="The histories a server serves, from its config file", domain=RepoGraphDomain)
class HistoriesConfig(BaseStorage):
    """
    AI-CORE-BEGIN
    ROLE: Name each history a server serves and where its graph file lives.
    CONTRACT: ``history(id)`` returns the ``History`` with that id, or ``None``. A config that breaks the shape is refused at load with a ``ValueError``.
    INVARIANTS: Reads only.
    AI-CORE-END
    """

    def __init__(self, path: Path) -> None:
        self._histories = _load(path)

    def get_wrapper_class(self) -> type[BaseStorage] | None:
        """Return ``None``: nested actions read through this same config."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the config is not a rollup target."""
        return False

    def history(self, history_id: str) -> History | None:
        """The history named ``history_id``, or ``None`` when the config has none."""
        return self._histories.get(history_id)


def _load(path: Path) -> dict[str, History]:
    """Every ``[[history]]`` of the file, by id; a file out of shape is refused naming why."""
    hosts = ("github", "local")
    fields = ("id", "host", "repository", "branch", "graph_file")
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{path}: not TOML: {error}") from None
    histories: dict[str, History] = {}
    for index, entry in enumerate(document.get("history", [])):
        missing = [name for name in fields if not isinstance(entry.get(name), str) or not entry[name]]
        if missing:
            raise ValueError(f"{path}: history {index + 1} lacks {', '.join(missing)}")
        if entry["host"] not in hosts:
            raise ValueError(f"{path}: history {entry['id']!r} has host {entry['host']!r}; known: {', '.join(hosts)}")
        if entry["id"] in histories:
            raise ValueError(f"{path}: history id {entry['id']!r} is given twice")
        histories[entry["id"]] = History(*(entry[name] for name in fields))
    return histories
