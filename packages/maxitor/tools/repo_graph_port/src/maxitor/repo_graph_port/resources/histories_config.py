# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/resources/histories_config.py
"""
HistoriesConfig — the histories the port serves and the keys that open them, from its config file.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The file named by ``MAXITOR_HISTORIES`` lists each configured history — an id, the
host, the repository, the branch and the graph file's path — with its read keys,
and the GitHub App the port reads private repositories with. A key is kept only
as its SHA-256, with the name of whoever holds it and an optional expiry date.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    TOML ──load──► {id: History}, {key hash: (id, name, expires)}
         ──history(id)──► History | None
         ──reader_of(hash, today)──► (id, name) | None   — an expired key opens nothing
         ──keys(id?)──► names and expiry dates, never hashes
         ──histories_of(repository, branch?)──► the histories a webhook concerns
         ──github()──► the App's id and the names of its secrets' variables

The file is read again when its modification time changes, so issuing or revoking a
key needs no restart. A file out of shape — not TOML, a history missing a field, an
unknown host, an id given twice or named ``public``, a key that is not a SHA-256 or
named twice in one history, a ``[github]`` table missing a field — is refused with a
``ValueError`` naming what is wrong; a running port keeps the last file it accepted.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from maxitor.repo_graph_port.history import History
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


@dataclass(frozen=True)
class _Loaded:
    """One accepted reading of the file."""

    histories: dict[str, History]
    readers: dict[str, tuple[str, str, date | None]]
    github: tuple[int, str, str] | None


@meta(description="The histories the port serves and their read keys, from its config file", domain=RepoGraphDomain)
class HistoriesConfig(BaseStorage):
    """
    AI-CORE-BEGIN
    ROLE: Name each configured history, where its graph file lives, and the keys that open it.
    CONTRACT: ``history(id)`` returns the ``History`` or ``None``; ``reader_of(hash, today)`` returns the history id and key name a key hash opens, or ``None`` when unknown or expired; ``keys`` lists names and expiry dates. A file out of shape is refused at the first load with a ``ValueError``; later, the last accepted file stays in force.
    INVARIANTS: Reads only; never holds or returns a key, and returns a key's hash to nobody.
    AI-CORE-END
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._stamp = path.stat().st_mtime_ns
        self._loaded = load_histories(path)

    def __repr__(self) -> str:
        """Name the file, never what it holds."""
        return f"HistoriesConfig({str(self._path)!r})"

    def get_wrapper_class(self) -> type[BaseStorage] | None:
        """Return ``None``: nested actions read through this same config."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the config is not a rollup target."""
        return False

    def history(self, history_id: str) -> History | None:
        """The history named ``history_id``, or ``None`` when the config has none."""
        return self._current().histories.get(history_id)

    def reader_of(self, key_sha256: str, today: date) -> tuple[str, str] | None:
        """The history id and key name the key with this SHA-256 opens on ``today``, or ``None``."""
        found = self._current().readers.get(key_sha256)
        if found is None:
            return None
        history_id, name, expires = found
        if expires is not None and today > expires:
            return None
        return history_id, name

    def histories_of(self, repository: str, branch: str | None = None) -> list[History]:
        """The configured histories of ``repository`` (on ``branch``, when given), by id."""
        found = [h for h in self._current().histories.values() if h.repository == repository and branch in (None, h.branch)]
        return sorted(found, key=lambda history: history.id)

    def github(self) -> tuple[int, str, str] | None:
        """The App's id and the names of the variables holding its private key and webhook secret, or ``None``."""
        return self._current().github

    def keys(self, history_id: str | None = None) -> list[tuple[str, str, date | None]]:
        """Every key as (history id, name, expiry), of one history or of all, sorted."""
        listed = [entry for entry in self._current().readers.values() if history_id in (None, entry[0])]
        return sorted(listed, key=lambda entry: (entry[0], entry[1]))

    def _current(self) -> _Loaded:
        """The file as last accepted, read again when it changed and still in shape."""
        try:
            stamp = self._path.stat().st_mtime_ns
        except FileNotFoundError:
            return self._loaded
        if stamp != self._stamp:
            self._stamp = stamp
            try:
                self._loaded = load_histories(self._path)
            except (OSError, ValueError):
                # A file broken while the port runs leaves the last accepted one in force.
                pass
        return self._loaded


def load_histories(path: Path) -> _Loaded:
    """Read and check the whole file; refuse it naming the first thing out of shape."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{path}: not TOML: {error}") from None
    github = _github(path, document.get("github"))
    histories: dict[str, History] = {}
    readers: dict[str, tuple[str, str, date | None]] = {}
    for index, entry in enumerate(document.get("history", [])):
        history = _history(path, index, entry, histories)
        histories[history.id] = history
        names: set[str] = set()
        for key in entry.get("keys", []):
            name, digest, expires = _key(path, history.id, key, names)
            names.add(name)
            readers[digest] = (history.id, name, expires)
    return _Loaded(histories, readers, github)


def _history(path: Path, index: int, entry: dict[str, Any], seen: dict[str, History]) -> History:
    """One ``[[history]]``, checked."""
    hosts = ("github", "local")
    fields = ("id", "host", "repository", "branch", "graph_file")
    missing = [name for name in fields if not isinstance(entry.get(name), str) or not entry[name]]
    if missing:
        raise ValueError(f"{path}: history {index + 1} lacks {', '.join(missing)}")
    if entry["host"] not in hosts:
        raise ValueError(f"{path}: history {entry['id']!r} has host {entry['host']!r}; known: {', '.join(hosts)}")
    if entry["id"] in seen or entry["id"] == "public":
        raise ValueError(f"{path}: history id {entry['id']!r} is given twice or reserved")
    return History(*(entry[name] for name in fields))


def _key(path: Path, history_id: str, key: dict[str, Any], names: set[str]) -> tuple[str, str, date | None]:
    """One ``[[history.keys]]``, checked: a name, a SHA-256 in hex, an optional date."""
    name, digest, expires = key.get("name"), key.get("sha256"), key.get("expires")
    if not isinstance(name, str) or not name or name in names:
        raise ValueError(f"{path}: history {history_id!r} has a key with no name, or a name given twice")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError(f"{path}: key {name!r} of history {history_id!r} has no sha256 of 64 hex digits")
    if isinstance(expires, str):
        try:
            expires = date.fromisoformat(expires)
        except ValueError:
            raise ValueError(f"{path}: key {name!r} of history {history_id!r} expires on no date") from None
    if expires is not None and not isinstance(expires, date):
        raise ValueError(f"{path}: key {name!r} of history {history_id!r} expires on no date")
    return name, digest, expires


def _github(path: Path, table: object) -> tuple[int, str, str] | None:
    """The ``[github]`` table, when present: the App's id and the names of the variables holding its secrets."""
    if table is None:
        return None
    if not isinstance(table, dict):
        raise ValueError(f"{path}: [github] is not a table")
    if not isinstance(table.get("app_id"), int):
        raise ValueError(f"{path}: [github] lacks app_id")
    for name in ("private_key_env", "webhook_secret_env"):
        if not isinstance(table.get(name), str) or not table[name]:
            raise ValueError(f"{path}: [github] lacks {name}")
    return table["app_id"], table["private_key_env"], table["webhook_secret_env"]
