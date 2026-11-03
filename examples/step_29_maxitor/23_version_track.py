"""
23_version_track.py — what the version track shows when a history names its version file

Maxitor draws a history's versions on a track. A large point changed the graph, a small point changed only the version,
and a number stands under a point where the version rose. This example runs a real port and Maxitor over a small
repository, and reads what the track reads.

The cases, with the real output at the bottom:

  1. a history with a version file: large and small points, and where a number stands;
  2. the same repository with no version file: every point large, no numbers from the file, no icon;
  3. what hiding leaves: the points that stay, the flags they carry, and a chosen point;
  4. two versions with one graph: the comparison says so;
  5. a version file that cannot be read: the graph still opens, and the problem reaches the reader;
  6. a public link with its version file, and the addresses refused.

Everything runs in a temporary folder; ``git`` required.

Output:

    1. A history with a version file
      History joined described for anna
      History joined listed for anna
      history joined by anna opened: 5 versions
       first                          large  1.0.0
       model and number               large  1.1.0
       code and number                small  1.1.1
       model only                     large  —
       code, number                   small  1.1.2
       version_file: version.toml, so the icon that hides small points is offered
    2. The same repository with no version file
      History plain described for anna
      History plain listed for anna
      history plain by anna opened: 3 versions
       first                          large  —
       model and number               large  —
       model only                     large  —
       version_file: None, so no point is small and no icon is offered
    3. What hiding leaves
       tag release-1.1.1: in its card, no flag, since a local repository publishes no release
       nothing chosen:
       first, model and number, model only
       flags on the points that stay: {}
       "code and number" chosen, it stays while it is chosen:
       first, model and number, code and number, model only
       flags on the points that stay: {}
    4. Two versions with one graph
       model and number and code and number: same graph True
       code and number and model only: same graph False
    5. A version file that cannot be read
      History broken described for anna
      History broken listed for anna
      history broken by anna opened: 3 versions
       version_problem: pom.xml is neither TOML nor JSON; link a component's version.toml, or use no version file
       3 points, every one large: True
    6. A public link with its version file
       name: https://github.com/owner/service/blob/main/graph.json?version_link=https%3A%2F%2Fgithub.com%2Fowner%2Fservice%2Fblob%2Fmain%2Fpyproject.toml&version_key=project.version
       refused: A public history's link takes only one 'version_link=' and one 'version_key=' in its query.
       refused: 'version_key=' names a key of the file in 'version_link=', so it needs one.
"""

from __future__ import annotations

import contextlib
import io
import json
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn
from fastapi.testclient import TestClient
from maxitor.repo_graph_port.cli import main as port_cli
from maxitor.repo_graph_port.server import create_app as create_port
from maxitor.web.api.app import create_app as create_maxitor
from maxitor.web.model.core.history_address import HistoryAddressError, parse_history

FOLDER = Path(tempfile.mkdtemp())
GRAPH_LINK = "https://github.com/owner/service/blob/main/graph.json"
FILE_LINK = "https://github.com/owner/service/blob/main/pyproject.toml"


def graph(entities: int) -> str:
    """A valid graph of ``entities`` nodes."""
    nodes = [{"id": f"shop.E{n}", "type": "Entity", "label": f"E{n}", "properties": {}} for n in range(entities)]
    return json.dumps({"schema_version": "1.2", "nodes": nodes, "edges": []}, indent=2) + "\n"


def component(number: str) -> str:
    """A component's ``version.toml``."""
    return f'kind = "component"\nversion = "{number}"\n'


def git(*arguments: str) -> None:
    """Run git in the example's repository."""
    subprocess.run(["git", "-C", str(FOLDER / "repo"), "-c", "user.name=T", "-c", "user.email=t@e", *arguments], check=True, capture_output=True)


def commit(message: str, files: dict[str, str]) -> None:
    """Write ``files`` and commit them."""
    for name, text in files.items():
        (FOLDER / "repo" / name).write_text(text, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", message)


def build_repository() -> None:
    """Five commits: model and number, code and number with a tag, model only, code and number."""
    (FOLDER / "repo").mkdir()
    git("init", "-q", "-b", "main")
    commit("first", {"graph.json": graph(2), "version.toml": component("1.0.0")})
    commit("model and number", {"graph.json": graph(3), "version.toml": component("1.1.0")})
    commit("code and number", {"version.toml": component("1.1.1")})
    git("tag", "release-1.1.1")
    commit("model only", {"graph.json": graph(4)})
    commit("code, number", {"version.toml": component("1.1.2")})


def start_port() -> tuple[str, dict[str, str]]:
    """A real port over the repository, with three histories; its address and each history's key."""
    config = FOLDER / "histories.toml"
    entries = {"joined": 'version_file = "version.toml"\n', "plain": "", "broken": 'version_file = "pom.xml"\n'}
    commit("a file that holds no version", {"pom.xml": "<project/>"})
    config.write_text(
        "".join(f'[[history]]\nid = "{name}"\nhost = "local"\nrepository = "{FOLDER / "repo"}"\nbranch = "main"\ngraph_file = "graph.json"\n{extra}' for name, extra in entries.items()),
        encoding="utf-8",
    )
    keys = {}
    for name in entries:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            port_cli(["--config", str(config), "key", "new", "--history", name, "--name", "anna"])
        keys[name] = out.getvalue().strip()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_port(config, FOLDER / "cache"), host="127.0.0.1", port=free, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return f"http://127.0.0.1:{free}/api/v1/history", keys


def open_history(maxitor: TestClient, port: str, keys: dict[str, str], name: str) -> dict[str, Any]:
    """Open a history as the browser does: its name in the query, its key in the header."""
    answer: dict[str, Any] = maxitor.get("/api/history/open", params={"history": f"{port}/{name}"}, headers={"X-Maxitor-History-Key": keys[name]}).json()
    return answer


def drawn(point: dict[str, Any], file: bool) -> str:
    """How the track draws a point: its size, and the number under it."""
    size = "large" if point.get("graph_changed", True) else "small"
    number = point["version"] if file and point.get("version_changed") else "—"
    return f"{size}  {number}"


def show(history: dict[str, Any]) -> None:
    """One line per point, as the track draws it."""
    for point in history["versions"]:
        print(f'   {point["message"].strip().ljust(30)} {drawn(point, history["version_file"] is not None)}')


def flags_of(point: dict[str, Any]) -> list[str]:
    """The tags that are flags on the track: only a tag published as a release on its host, never a name alone."""
    return [tag["name"] for tag in point["tags"] if tag["release"]]


def hidden_view(versions: list[dict[str, Any]], chosen: str | None) -> None:
    """What stays when the small points are hidden, as the track's own filter decides it."""
    kept = [point for point in versions if point.get("graph_changed", True) or point["sha"].startswith(chosen or "\0")]
    carried: dict[str, list[str]] = {}
    for point in versions:
        if point not in kept and flags_of(point):
            before = [each for each in kept if versions.index(each) < versions.index(point)]
            carried.setdefault((before[-1] if before else kept[0])["message"].strip(), []).extend(flags_of(point))
    print(f'   {", ".join(point["message"].strip() for point in kept)}')
    print(f"   flags on the points that stay: {carried}")


def same_graph(versions: list[dict[str, Any]], older: int, newer: int) -> bool:
    """Whether no point after the older one, up to the newer, changed the graph."""
    return all(point.get("graph_changed", True) is False for point in versions[older + 1 : newer + 1])


def main() -> None:
    """Walk the six cases."""
    build_repository()
    port, keys = start_port()
    with TestClient(create_maxitor()) as maxitor:
        print("1. A history with a version file")
        joined = open_history(maxitor, port, keys, "joined")
        show(joined)
        print(f'   version_file: {joined["version_file"]}, so the icon that hides small points is offered')

        print("2. The same repository with no version file")
        plain = open_history(maxitor, port, keys, "plain")
        show(plain)
        print(f'   version_file: {plain["version_file"]}, so no point is small and no icon is offered')

        print("3. What hiding leaves")
        versions = joined["versions"]
        print(f'   tag {versions[2]["tags"][0]["name"]}: in its card, no flag, since a local repository publishes no release')
        print("   nothing chosen:")
        hidden_view(versions, None)
        print('   "code and number" chosen, it stays while it is chosen:')
        hidden_view(versions, versions[2]["sha"][:12])

        print("4. Two versions with one graph")
        print(f'   {versions[1]["message"].strip()} and {versions[2]["message"].strip()}: same graph {same_graph(versions, 1, 2)}')
        print(f'   {versions[2]["message"].strip()} and {versions[3]["message"].strip()}: same graph {same_graph(versions, 2, 3)}')

        print("5. A version file that cannot be read")
        broken = open_history(maxitor, port, keys, "broken")
        print(f'   version_problem: {broken["version_problem"]}')
        print(f'   {len(broken["versions"])} points, every one large: {all(point["graph_changed"] for point in broken["versions"])}')

    print("6. A public link with its version file")
    history = parse_history(f"{GRAPH_LINK}?version_key=project.version&version_link={FILE_LINK}")
    print(f"   name: {history.name}" if history else "   not a history")
    for address in (f"{GRAPH_LINK}?branch=main", f"{GRAPH_LINK}?version_key=project.version"):
        try:
            parse_history(address)
        except HistoryAddressError as refused:
            print(f"   refused: {refused}")


if __name__ == "__main__":
    main()
