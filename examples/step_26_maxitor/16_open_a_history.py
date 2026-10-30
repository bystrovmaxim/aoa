"""
16_open_a_history.py — Maxitor opens a service's graph history and shows any version

``repo-graph-port`` serves a service's graph history from its repository (example 14). Maxitor opens that
history with one address — the port's history URL with the read key after ``#key=`` — and lets a reader
pick any version on a time axis: every merged pull request and direct push that changed the graph, the
pull requests still open that would change it, and Live, the service running now. This example runs a
real port and a stand-in Live service in the background and calls Maxitor's history routes the way its
page does. The port's and Maxitor's own log lines are printed indented; the key is never among them.

The cases, with the real output at the bottom:

  1. a service's repository: a direct push, two merged pull requests, a broken graph mended, tags — a
     version number and a release — and one pull request still open;
  2. the port over it, five histories (one per mode of the screen) and a read key each; Live serving the
     newest version's graph;
  3. Maxitor opens the history: the versions oldest first, each with what its card says — how it came,
     who made and merged it, its size, what it did to the graph — and its name on the track;
  4. Live runs exactly the newest version's graph: Maxitor names that version, the track shows one point;
  5. the open pull request, with its review state, read like a version;
  6. every mode: what Maxitor answers for Live with versions, versions alone, one version, Live alone, nothing;
  7. reading graphs: a version, the open pull request, a refused version;
  8. refusals: a wrong key, an address out of shape, a public link while Maxitor has no port of its own;
  9. the key in no log line, the port's or Maxitor's.

Everything runs in a temporary folder; ``git`` required.

Output:

    1. A service's repository
       main, oldest first: Add the graph · Merge pull request #1 from two-edges · Merge pull request #2 from billing · Break the graph · Mend the graph
       open: refs/pull/3/head — Drop the audit links
    2. The port, five histories, Live
       5 keys issued, each kept in the config as its hash only
    3. Maxitor opens orders: versions oldest first
      History orders described for anna
      History orders listed for anna
      history orders by anna opened: 5 versions and Live
      History orders version read for anna
       #1  0.1.0  Direct push  Olga Kim                      +6722 −0 · 1 file   +265 nodes · +385 links
       #1  0.2.0  Merged       Anna Petrova → Maxim          +0 −18 · 1 file     −2 links  ⚑ release-0.2
       #2  0.2.0  Merged       Ivan Sokolov → Maxim          +10 −0 · 1 file     +1 Entity
       #4  0.2.0  Direct push  Olga Kim                      refused: graph 1.1 at nodes/0: matche…
       #5  0.2.0  Direct push  Olga Kim                      +6714 −1 · 1 file   +266 nodes · −1 nodes · +383 links
    4. Live runs exactly the newest version's graph
       live_same_as is the newest version: True — the track draws them as one point, Live
    5. The pull request still open
       #3 Drop the audit links · state open · by Pavel Orlov · {'added': 0, 'removed': 4}
    6. Every mode
      History orders described for anna
      History orders listed for anna
      history orders by anna opened: 5 versions and Live
      History orders version read for anna
       orders        5 version(s) and Live
      History orders-plain described for anna
      History orders-plain listed for anna
      history orders-plain by anna opened: 5 versions
       orders-plain  5 version(s)
      History single described for anna
      History single listed for anna
      history single by anna opened: 1 version
       single        1 version(s)
      History waiting described for anna
      History waiting listed for anna
      history waiting by anna opened: 0 versions and Live
       waiting       0 version(s) and Live
      History empty described for anna
      History empty listed for anna
      history empty by anna opened: 0 versions
       empty         0 version(s)
    7. Reading graphs
      History orders version read for anna
       the newest version: 200
      History orders version read for anna
       the open pull request: 200
       the broken version: 422 graph 1.1 at nodes/0: matches none of the shapes allowed her
    8. Refusals
      Wrong key for history orders from 127.0.0.1
      History orders at http://127.0.0.1:…#… refused the key from testclient
       a wrong key: 404 {'detail': 'not found'}
       an address out of shape: 400
       a public link, Maxitor without a port of its own: 400 {'detail': 'Public histories are not set up on this Maxitor'}
    9. The key in the logs
       0 of 5 keys appear in everything printed, both servers' logs included

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  how-to: ../../docs/how-to/open-a-graph-history.md

Run:
    uv run --extra dev python examples/step_26_maxitor/16_open_a_history.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import uvicorn
from fastapi.testclient import TestClient
from maxitor.front.api.app import create_app as create_maxitor
from maxitor.repo_graph_port.cli import main as history_command
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.server import create_app as create_port

# The repository root: the folder that holds graph-builder.toml, wherever this runs from.
REPO_ROOT = next(
    path for path in (Path.cwd(), *Path(__file__).resolve().parents) if (path / "graph-builder.toml").is_file()
)
FRONT_GRAPH = json.loads((REPO_ROOT / "packages/maxitor/front/graph.json").read_text(encoding="utf-8"))
WORK = Path(tempfile.mkdtemp(prefix="open-a-history-"))


class Tee(io.TextIOBase):
    """Everything printed — this example's lines and both servers' logs — shown and kept, to search for the key."""

    def __init__(self, out: Any) -> None:
        self.out, self.kept = out, io.StringIO()

    def write(self, text: str) -> int:
        self.kept.write(text)
        return self.out.write(text)

    def flush(self) -> None:
        self.out.flush()


TEE = Tee(sys.stdout)
sys.stdout = TEE


def graph(edges: int | None = None, extra: int = 0) -> str:
    """Maxitor's own graph as a file holds it: its last edges dropped, or ``extra`` entities added, so each version differs."""
    document = dict(FRONT_GRAPH)
    if edges is not None:
        document["edges"] = FRONT_GRAPH["edges"][:edges]
    entity = next(node for node in FRONT_GRAPH["nodes"] if node["type"] == "Entity")
    document["nodes"] = FRONT_GRAPH["nodes"] + [dict(entity, id=f"example.entity.{n}") for n in range(extra)]
    return json.dumps(document, indent=2) + "\n"


def git(repository: Path, *arguments: str, who: str = "Olga Kim") -> str:
    """One git command in ``repository`` as ``who``."""
    identity = ["-c", f"user.name={who}", "-c", "user.email=example@example.com"]
    return subprocess.run(
        ["git", "-C", str(repository), *identity, *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(repository: Path, message: str, files: dict[str, str], who: str = "Olga Kim") -> str:
    """Write ``files``, commit them as ``who``; the commit."""
    for name, text in files.items():
        (repository / name).write_text(text, encoding="utf-8")
    git(repository, "add", *files, who=who)
    git(repository, "commit", "-q", "-m", message, who=who)
    return git(repository, "rev-parse", "HEAD")


def merge(repository: Path, number: int, branch: str, title: str, files: dict[str, str], who: str) -> str:
    """A pull request: ``who`` commits on ``branch``, Maxim merges it with GitHub's merge message; the merge commit."""
    git(repository, "checkout", "-q", "-b", branch, "main")
    commit(repository, title, files, who=who)
    git(repository, "checkout", "-q", "main")
    git(
        repository,
        "merge",
        "-q",
        "--no-ff",
        "-m",
        f"Merge pull request #{number} from {branch}\n\n{title}",
        branch,
        who="Maxim",
    )
    return git(repository, "rev-parse", "HEAD")


def described(change: dict[str, Any]) -> list[str]:
    """What a version did to the graph, as its card says it: nodes by kind — a total when many kinds moved — then links."""
    added, removed = change["added"], change["removed"]
    nodes = [f"+{n} {kind}" for kind, n in added.items()] + [f"−{n} {kind}" for kind, n in removed.items()]
    if len(nodes) > 3:
        nodes = [f"+{sum(added.values())} nodes"] * bool(added) + [f"−{sum(removed.values())} nodes"] * bool(removed)
    links = change["links"]
    return (
        nodes
        + [f"+{links['added']} links"] * bool(links["added"])
        + [f"−{links['removed']} links"] * bool(links["removed"])
    )


def serve(app: Any) -> str:
    """Run ``app`` with uvicorn in the background on a free port; its address."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return f"http://127.0.0.1:{sock.getsockname()[1]}"


print("1. A service's repository")
service = WORK / "service"
service.mkdir()
git(service, "init", "-q", "-b", "main")
commit(service, "Add the graph", {"graph.json": graph()})
git(service, "tag", "v0.1.0")
merge(
    service, 1, "two-edges", "Two edges fewer", {"graph.json": graph(len(FRONT_GRAPH["edges"]) - 2)}, who="Anna Petrova"
)
git(service, "tag", "v0.2.0")
git(service, "tag", "release-0.2")
merge(
    service,
    2,
    "billing",
    "Add the billing entity",
    {"graph.json": graph(len(FRONT_GRAPH["edges"]) - 2, extra=1)},
    who="Ivan Sokolov",
)
broken = commit(
    service, "Break the graph", {"graph.json": json.dumps({"schema_version": "1.1", "nodes": [{"id": 1}], "edges": []})}
)
newest = commit(service, "Mend the graph", {"graph.json": graph(len(FRONT_GRAPH["edges"]) - 2, extra=1)})
# A pull request still open: GitHub keeps its head as refs/pull/<n>/head; a local repository can keep it the same way.
git(service, "checkout", "-q", "-b", "audit", "main")
proposal = commit(
    service, "Drop the audit links", {"graph.json": graph(len(FRONT_GRAPH["edges"]) - 6, extra=1)}, who="Pavel Orlov"
)
git(service, "checkout", "-q", "main")
git(service, "update-ref", "refs/pull/3/head", proposal)
print(
    "   main, oldest first:", " · ".join(git(service, "log", "--first-parent", "--reverse", "--format=%s").splitlines())
)
print("   open: refs/pull/3/head —", git(service, "log", "-1", "--format=%s", proposal))
nothing = WORK / "nothing"
nothing.mkdir()
git(nothing, "init", "-q", "-b", "main")
commit(nothing, "Start", {"README.md": "no graph yet\n"})
single = WORK / "single"
single.mkdir()
git(single, "init", "-q", "-b", "main")
commit(single, "Add the graph", {"graph.json": graph()})

print("2. The port, five histories, Live")


class LiveService(BaseHTTPRequestHandler):
    """The running service: its graph-json, wrapped as an AOA service answers it, the same graph as the newest version."""

    def do_GET(self) -> None:
        body = json.dumps({"coordinator_json": git(service, "show", f"{newest}:graph.json")}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


live_server = ThreadingHTTPServer(("127.0.0.1", 0), LiveService)
threading.Thread(target=live_server.serve_forever, daemon=True).start()
live = f"http://127.0.0.1:{live_server.server_address[1]}/graph-json"
histories = [  # id, repository, live: one history per mode of the screen
    ("orders", service, live),  # Live and several versions (M4)
    ("orders-plain", service, None),  # several versions, no Live (M2)
    ("single", single, None),  # one version (M3)
    ("waiting", nothing, live),  # Live, no version yet (M6)
    ("empty", nothing, None),  # nothing yet (M7)
]
config = WORK / "histories.toml"
config.write_text(
    "".join(
        f'[[history]]\nid = "{name}"\nhost = "local"\nrepository = "{path}"\nbranch = "main"\ngraph_file = "graph.json"\n'
        + (f'live = "{address}"\n' if address else "")
        + "\n"
        for name, path, address in histories
    ),
    encoding="utf-8",
)
key_file = WORK / "keys.txt"
# The command prints each key once; the example keeps the keys out of its own output.
with key_file.open("w") as out, contextlib.redirect_stdout(out):
    for name, _path, _live in histories:
        history_command(["--config", str(config), "key", "new", "--history", name, "--name", "anna"])
keys = dict(zip([name for name, _p, _l in histories], key_file.read_text(encoding="utf-8").split(), strict=True))
held = config.read_text(encoding="utf-8")
print(
    f"   {len(keys)} keys issued, each kept in the config as its hash only"
    if not any(k in held for k in keys.values())
    else "   a key is in the config!"
)
port = serve(create_port(config, WORK / "cache", GitHubHost()))

os.environ.pop("MAXITOR_PUBLIC_PORT", None)
with TestClient(create_maxitor()) as maxitor:

    def open_history(name: str) -> Any:
        """Open history ``name`` as Maxitor's page does: its address in the query, its key in the header."""
        return maxitor.get(
            "/api/history/open",
            params={"history": f"{port}/api/v1/history/{name}"},
            headers={"X-Maxitor-History-Key": keys[name]},
        )

    print("3. Maxitor opens orders: versions oldest first")
    opened = open_history("orders").json()
    number = None
    for place, version in enumerate(opened["versions"], start=1):
        tag = next((t["name"] for t in version["tags"] if t["name"][1:2].isdigit()), None)
        number = tag[1:] if tag else number
        name = f"#{version['pr']['number']}" if version["pr"] else f"#{place}"
        how = "Merged" if version["pr"] else "Direct push"
        made = version["contribution"]
        who = f"{made['author']} → {made['merged_by']}" if made["merged_by"] else made["author"]
        said = [] if version["refused"] else described(version["change"])
        size = (
            f"refused: {version['refused'][:28]}…"
            if version["refused"]
            else f"+{made['additions']} −{made['deletions']} · {made['files']} file"
        )
        flags = [t["name"] for t in version["tags"] if t["name"].startswith("release")]
        print(
            f"   {name:<4}{number or '':<7}{how:<13}{who:<30}{size:<20}{' · '.join(said)}{'  ⚑ ' + flags[0] if flags else ''}"
        )

    print("4. Live runs exactly the newest version's graph")
    print(
        f"   live_same_as is the newest version: {opened['live_same_as'] == newest} — the track draws them as one point, Live"
    )

    print("5. The pull request still open")
    for pending in opened["proposals"]:
        print(
            f"   #{pending['pr']['number']} {pending['pr']['title']} · state {pending['pr']['state']} · by {pending['contribution']['author']} · {pending['change']['links']}"
        )

    print("6. Every mode")
    for name, _path, _live in histories:
        body = open_history(name).json()
        print(f"   {name:<13} {body['count']} version(s){' and Live' if body['live'] else ''}")

    print("7. Reading graphs")
    header = {"X-Maxitor-History-Key": keys["orders"]}
    by_sha = {v["sha"]: v for v in [*opened["versions"], *opened["proposals"]]}
    for label, sha in (
        ("the newest version", newest),
        ("the open pull request", proposal),
        ("the broken version", broken),
    ):
        read = maxitor.get("/api/v1/full-graph", params={"source": by_sha[sha]["source"]}, headers=header)
        print(f"   {label}: {read.status_code}" + ("" if read.status_code == 200 else f" {read.json()['detail'][:60]}"))

    print("8. Refusals")
    wrong = maxitor.get(
        "/api/history/open",
        params={"history": f"{port}/api/v1/history/orders"},
        headers={"X-Maxitor-History-Key": "a-guess"},
    )
    shapeless = maxitor.get("/api/history/open", params={"history": "ftp://example.com/graph"})
    public = maxitor.get("/api/history/open", params={"history": "https://github.com/acme/open/blob/main/graph.json"})
    print(f"   a wrong key: {wrong.status_code} {wrong.json()}")
    print(f"   an address out of shape: {shapeless.status_code}")
    print(f"   a public link, Maxitor without a port of its own: {public.status_code} {public.json()}")

print("9. The key in the logs")
printed = TEE.kept.getvalue()
print(
    f"   {sum(printed.count(key) for key in keys.values())} of {len(keys)} keys appear in everything printed, both servers' logs included"
)
