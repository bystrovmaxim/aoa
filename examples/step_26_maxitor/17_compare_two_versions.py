"""
17_compare_two_versions.py — Maxitor compares two versions of a service's graph

A graph history (example 16) holds every version of a service's graph. Maxitor compares any two of them: A, the
older, and B, the newer. One read gives every node and link that was added, removed or changed, with counts —
what the ERD paints and the version button counts; a second gives one element's differences, property by
property — what its card shows. This example runs a real port over a small repository and calls both reads the
way Maxitor's page does: B as the source, A as ``a``, the history's key in the header.

The cases, with the real output at the bottom:

  1. a service's repository: three versions — the graph, two links fewer, a new entity and one changed;
  2. the port over it and a read key;
  3. 0.1.0 → 0.2.0: two links removed, nothing else;
  4. 0.2.0 → 0.3.0: an entity added, one changed — and what changed in it;
  5. 0.1.0 → 0.3.0: far apart, the changes add up;
  6. the newest version → Live: the same graph, "no changes";
  7. a wrong key: refused, as every read of the history.

Everything runs in a temporary folder; ``git`` required.

Output:

    1. A service's repository
       main, oldest first: Add the graph (v0.1.0) · Two links fewer (v0.2.0) · Add the billing entity (v0.3.0)
    2. The port and a read key
      History orders described for anna
      History orders listed for anna
      history orders by anna opened: 3 versions and Live
      History orders version read for anna
    3. 0.1.0 → 0.2.0
      History orders version read for anna
      History orders version read for anna
      Comparison computed in 5 ms: nodes +0 −0 ~0, edges +0 −2 ~0
       nodes +0 −0 ~0 · links +0 −2 ~0
    4. 0.2.0 → 0.3.0
      History orders version read for anna
      Comparison computed in 5 ms: nodes +1 −0 ~1, edges +0 −0 ~0
       nodes +1 −0 ~1 · links +0 −0 ~0
       changed: maxitor.front.model.core.entities.node_entity.NodeCoreEntity
         properties.description: 'Hierarchical UI node row (id, optional parent, label, coarse type)' → 'Orders a customer places, now billed.'
       added: example.billing
    5. 0.1.0 → 0.3.0
      Comparison computed in 5 ms: nodes +1 −0 ~1, edges +0 −2 ~0
       nodes +1 −0 ~1 · links +0 −2 ~0
    6. 0.3.0 → Live
      Comparison computed in 5 ms: nodes +0 −0 ~0, edges +0 −0 ~0
       nodes +0 −0 ~0 · links +0 −0 ~0 — no changes
    7. A wrong key
      Wrong key for history orders from 127.0.0.1
      History orders at http://127.0.0.1:…#… refused the key from testclient
       404 {'detail': 'not found'}

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  how-to: ../../docs/how-to/compare-two-versions.md

Run:
    uv run --extra dev python examples/step_26_maxitor/17_compare_two_versions.py
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import subprocess
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
WORK = Path(tempfile.mkdtemp(prefix="compare-two-versions-"))
ENTITY = next(node for node in FRONT_GRAPH["nodes"] if node["type"] == "Entity")


def graph(edges_dropped: int = 0, billing: bool = False, described: str | None = None) -> str:
    """Maxitor's own graph as a file holds it: its last edges dropped, a billing entity added, an entity redescribed."""
    document = dict(FRONT_GRAPH)
    document["edges"] = FRONT_GRAPH["edges"][: len(FRONT_GRAPH["edges"]) - edges_dropped]
    nodes = [dict(node) for node in FRONT_GRAPH["nodes"]]
    if described is not None:
        changed = next(node for node in nodes if node["id"] == ENTITY["id"])
        changed["properties"] = {**changed.get("properties", {}), "description": described}
    if billing:
        nodes.append(dict(ENTITY, id="example.billing"))
    document["nodes"] = nodes
    return json.dumps(document, indent=2) + "\n"


def git(repository: Path, *arguments: str) -> str:
    """One git command in ``repository``."""
    identity = ["-c", "user.name=Olga Kim", "-c", "user.email=example@example.com"]
    return subprocess.run(
        ["git", "-C", str(repository), *identity, *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def release(repository: Path, message: str, text: str, tag: str) -> str:
    """Commit ``text`` as the graph file and tag it ``tag``; the commit."""
    (repository / "graph.json").write_text(text, encoding="utf-8")
    git(repository, "add", "graph.json")
    git(repository, "commit", "-q", "-m", message)
    git(repository, "tag", tag)
    return git(repository, "rev-parse", "HEAD")


def serve(app: Any) -> str:
    """Run ``app`` with uvicorn in the background on a free port; its address."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return f"http://127.0.0.1:{sock.getsockname()[1]}"


def counts(answer: dict[str, Any]) -> str:
    """The counts as the version button shows them, for nodes and for links."""
    nodes, links = answer["counts"]["nodes"], answer["counts"]["edges"]
    return " · ".join(
        f"{label} +{n['added']} −{n['removed']} ~{n['changed']}" for label, n in (("nodes", nodes), ("links", links))
    )


print("1. A service's repository")
service = WORK / "service"
service.mkdir()
git(service, "init", "-q", "-b", "main")
v1 = release(service, "Add the graph", graph(), "v0.1.0")
v2 = release(service, "Two links fewer", graph(edges_dropped=2), "v0.2.0")
v3 = release(
    service,
    "Add the billing entity",
    graph(edges_dropped=2, billing=True, described="Orders a customer places, now billed."),
    "v0.3.0",
)
tags = {v1: "v0.1.0", v2: "v0.2.0", v3: "v0.3.0"}
print(
    "   main, oldest first:",
    " · ".join(
        f"{subject} ({tags[sha]})"
        for sha, subject in (
            line.split(" ", 1) for line in git(service, "log", "--reverse", "--format=%H %s").splitlines()
        )
    ),
)

print("2. The port and a read key")


class LiveService(BaseHTTPRequestHandler):
    """The running service: the newest version's graph, wrapped as an AOA service answers it."""

    def do_GET(self) -> None:
        body = json.dumps({"coordinator_json": git(service, "show", f"{v3}:graph.json")}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


live_server = ThreadingHTTPServer(("127.0.0.1", 0), LiveService)
threading.Thread(target=live_server.serve_forever, daemon=True).start()
config = WORK / "histories.toml"
config.write_text(
    f'[[history]]\nid = "orders"\nhost = "local"\nrepository = "{service}"\nbranch = "main"\n'
    f'graph_file = "graph.json"\nlive = "http://127.0.0.1:{live_server.server_address[1]}/graph-json"\n',
    encoding="utf-8",
)
key_file = WORK / "key.txt"
# The command prints the key once; the example keeps it out of its own output.
with key_file.open("w") as out, contextlib.redirect_stdout(out):
    history_command(["--config", str(config), "key", "new", "--history", "orders", "--name", "anna"])
key = key_file.read_text(encoding="utf-8").strip()
port = serve(create_port(config, WORK / "cache", GitHubHost()))

os.environ.pop("MAXITOR_PUBLIC_PORT", None)
with TestClient(create_maxitor()) as maxitor:
    header = {"X-Maxitor-History-Key": key}
    opened = maxitor.get("/api/history/open", params={"history": f"{port}/api/v1/history/orders"}, headers=header).json()
    source = {version["sha"]: version["source"] for version in opened["versions"]}
    source["live"] = opened["live"]

    def compare(a: str, b: str, key_used: str = key) -> Any:
        """The comparison read as the page sends it: B as the source, A as ``a``, the key in the header."""
        return maxitor.get(
            "/api/v1/compare",
            params={"source": source[b], "a": source[a]},
            headers={"X-Maxitor-History-Key": key_used},
        )

    print("3. 0.1.0 → 0.2.0")
    print("  ", counts(compare(v1, v2).json()))

    print("4. 0.2.0 → 0.3.0")
    answer = compare(v2, v3).json()
    print("  ", counts(answer))
    for node, status in answer["nodes"].items():
        print(f"   {status}: {node}")
        if status == "changed":
            element = maxitor.get(
                "/api/v1/compare-element",
                params={"source": source[v3], "a": source[v2], "kind": "node", "id": node},
                headers=header,
            ).json()
            for difference in element["differences"]:
                print(f"     {'.'.join(difference['path'])}: {difference.get('before')!r} → {difference.get('after')!r}")

    print("5. 0.1.0 → 0.3.0")
    print("  ", counts(compare(v1, v3).json()))

    print("6. 0.3.0 → Live")
    answer = compare(v3, "live").json()
    nothing = all(n == 0 for kind in answer["counts"].values() for n in kind.values())
    print("  ", counts(answer), "— no changes" if nothing else "")

    print("7. A wrong key")
    refused = compare(v1, v2, key_used="a-guess")
    print(f"   {refused.status_code} {refused.json()}")
