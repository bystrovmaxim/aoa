# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/cli.py
"""
``repo-graph-port history …`` — the read keys and the check of the histories config, from the command line.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Keys are administered on the server, never over HTTP. ``key new`` prints a new key
once and writes only its SHA-256, with the holder's name and an optional expiry;
``key revoke`` removes one; ``key list`` shows names and dates, never keys or hashes;
``check`` says whether the config is in shape and every history's graph file is
on its branch.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    MAXITOR_HISTORIES (or --config) ──► the TOML text
        key new    ──► a [[history.keys]] block after that history's last block ──► checked ──► written
        key revoke ──► that block removed ──► checked ──► written
        key list   ──► HistoriesConfig.keys
        check      ──► load_histories + each graph file on its branch, through GitMirror —
                       a GitHub one with the App's token, as the port reads it

The file is edited as text, so its comments and order survive; every edit is checked
by loading the result before it is written. Exit codes: 0 done, 1 a check failed,
2 the config is refused or the command is wrong.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import os
import re
import secrets
import sys
import tempfile
from datetime import date
from pathlib import Path

import httpx
from maxitor.repo_graph_port.git_error import GitError
from maxitor.repo_graph_port.history import History
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig, load_histories


def main(argv: list[str]) -> int:
    """Run one ``history …`` command; return its exit code."""
    parser = argparse.ArgumentParser(prog="repo-graph-port history", description="Read keys and the histories config.")
    parser.add_argument("--config", type=Path, default=None, help="the histories config (default: $MAXITOR_HISTORIES)")
    commands = parser.add_subparsers(dest="command", required=True)
    key = commands.add_parser("key", help="issue, revoke or list read keys").add_subparsers(dest="action", required=True)
    new = key.add_parser("new", help="print a new key once; keep only its hash")
    new.add_argument("--history", required=True)
    new.add_argument("--name", required=True)
    new.add_argument("--expires", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    revoke = key.add_parser("revoke", help="remove a key")
    revoke.add_argument("--history", required=True)
    revoke.add_argument("--name", required=True)
    listed = key.add_parser("list", help="names and expiry dates")
    listed.add_argument("--history", default=None)
    commands.add_parser("check", help="the config is in shape; each graph file is on its branch")
    # A wrong command line ends here: argparse prints why and exits with 2.
    arguments = parser.parse_args(argv)
    path = arguments.config or Path(os.environ.get("MAXITOR_HISTORIES", ""))
    try:
        config = HistoriesConfig(path)
    except (OSError, ValueError) as refused:
        print(f"refused: {refused}", file=sys.stderr)
        return 2
    if arguments.command == "check":
        return _check(path)
    if arguments.action == "list":
        for history_id, name, expires in config.keys(arguments.history):
            print(f"{history_id}\t{name}\t{expires or 'never'}")
        return 0
    if config.history(arguments.history) is None:
        print(f"refused: no history {arguments.history!r}", file=sys.stderr)
        return 2
    if arguments.action == "new":
        return _new(config, path, arguments.history, arguments.name, arguments.expires)
    return _revoke(config, path, arguments.history, arguments.name)


def _new(config: HistoriesConfig, path: Path, history_id: str, name: str, expires: date | None) -> int:
    """Add a key for ``name`` to ``history_id``; print the key, once."""
    if any(entry[:2] == (history_id, name) for entry in config.keys(history_id)):
        print(f"refused: history {history_id!r} already has a key named {name!r}", file=sys.stderr)
        return 2
    key = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    block = f'\n[[history.keys]]\nname = "{name}"\nsha256 = "{hashlib.sha256(key.encode()).hexdigest()}"\n'
    if expires is not None:
        block += f"expires = {expires.isoformat()}\n"
    blocks = _blocks(path.read_text(encoding="utf-8"))
    last = max(index for index, (owner, _, _) in enumerate(blocks) if owner == history_id)
    blocks.insert(last + 1, (history_id, "key", block))
    _write(path, blocks)
    print(key)
    return 0


def _revoke(config: HistoriesConfig, path: Path, history_id: str, name: str) -> int:
    """Remove the key named ``name`` from ``history_id``."""
    blocks = _blocks(path.read_text(encoding="utf-8"))
    kept = [b for b in blocks if not (b[0] == history_id and b[1] == "key" and _name(b[2]) == name)]
    if len(kept) == len(blocks):
        print(f"refused: history {history_id!r} has no key named {name!r}", file=sys.stderr)
        return 2
    _write(path, kept)
    return 0


def _check(path: Path) -> int:
    """Each history's graph file is on its branch, read as the port reads it; print one line per history."""
    loaded = load_histories(path)
    histories = sorted(loaded.histories.items())
    github = {history.repository for _, history in histories if history.host == "github"}
    tokens = asyncio.run(_tokens(GitHubHost.from_settings(loaded.github), github))
    failed = 0
    with tempfile.TemporaryDirectory() as cache:
        mirror = GitMirror(Path(cache))
        for history_id, history in histories:
            present, said = _check_one(mirror, tokens, history)
            failed += not present
            print(f"{'ok ' if present else 'FAIL'} {history_id}: {said}")
    return 1 if failed else 0


async def _tokens(host: GitHubHost, repositories: set[str]) -> dict[str, str | httpx.HTTPError | None]:
    """
    Each repository's installation token, or the error GitHub answered with. All are read in one event loop:
    the host keeps one HTTP client, and a client opened in a loop that has closed cannot be used again.
    """
    tokens: dict[str, str | httpx.HTTPError | None] = {}
    for repository in sorted(repositories):
        try:
            tokens[repository] = await host.token_for(repository)
        except httpx.HTTPError as error:
            tokens[repository] = error
    return tokens


def _check_one(mirror: GitMirror, tokens: dict[str, str | httpx.HTTPError | None], history: History) -> tuple[bool, str]:
    """Whether one history's graph file is on its branch, and what to say about it."""
    auth: dict[str, str] = {}
    url = None
    if history.host == "github":
        url = f"https://github.com/{history.repository}.git"
        token = tokens[history.repository]
        if isinstance(token, httpx.HTTPError):
            return False, f"the App is not installed on {history.repository}"
        if token is None:
            return False, "no [github] App to read a private repository with"
        auth = GitHubHost.git_auth(token)
    try:
        mirror.open(history.repository, url, auth)
        present = mirror.file_at(history.repository, history.branch, history.graph_file, auth) is not None
    except GitError as error:
        return False, str(error)
    return present, "ok" if present else f"no {history.graph_file} on {history.branch}"


def _blocks(text: str) -> list[tuple[str | None, str, str]]:
    """The file cut at each table header: (history id or None, ``head`` | ``history`` | ``key`` | ``other``, text)."""
    blocks: list[tuple[str | None, str, str]] = []
    owner: str | None = None
    for part in re.split(r"(?m)^(?=\[)", text):
        header = part.split("\n", 1)[0].strip()
        if header == "[[history]]":
            found = re.search(r'(?m)^id\s*=\s*"([^"]*)"', part)
            owner = found.group(1) if found else None
            blocks.append((owner, "history", part))
        elif header == "[[history.keys]]":
            blocks.append((owner, "key", part))
        else:
            if header.startswith("["):
                owner = None
            blocks.append((owner, "other" if header.startswith("[") else "head", part))
    return blocks


def _name(block: str) -> str | None:
    """The ``name`` of a key block."""
    found = re.search(r'(?m)^name\s*=\s*"([^"]*)"', block)
    return found.group(1) if found else None


def _write(path: Path, blocks: list[tuple[str | None, str, str]]) -> None:
    """Check the edited file by loading it, then put it in place of the old one."""
    text = "".join(block for _, _, block in blocks)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    try:
        load_histories(Path(temporary))
    except ValueError:
        os.unlink(temporary)
        raise
    os.replace(temporary, path)
