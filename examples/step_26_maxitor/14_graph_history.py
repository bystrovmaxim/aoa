"""
14_graph_history.py — a service's graph history, read from its repository by repo-graph-port

A service keeps its graph in a file beside its code, so the file's git history is the graph's history:
every merge that changed it is a version. ``repo-graph-port`` reads that history and serves it — each
version with its pull request and the repository's tags, and the graph of any version, byte for byte.
A private repository is opened by a read key; a public one by a link to its graph file. The port's
own log (the indented lines below) names each history and its reader — never a key.

The cases, with the real output at the bottom:

  1. a service's repository with two graph files (``graph.json`` for ``orders``, ``billing.json`` for
     ``billing``): a pull request merged, a commit made straight on ``main``, tags, a broken graph;
  2. the port over it, GitHub stood in — its App, a merged pull request, a release; a read key for ``orders``;
  3. ``describe``: what the history is;
  4. the versions, oldest first: the merged pull request names its version, a direct commit keeps its
     message, a tag on a later commit belongs to the version before it, the broken graph is refused;
  5. one version's graph: the committed bytes, cacheable forever;
  6. ``after``: only the newer versions;
  7. a repeated read naming its ``ETag``: ``304``;
  8. the key opens ``orders`` and not ``billing`` of the same repository; no key, the same ``404``;
  9. guessing keys: the eleventh wrong key from one address in a minute is ``429``;
 10. a public repository, by a link, with no key and no config;
 11. a push that changes only ``billing.json``: GitHub's signed webhook gives ``billing`` a version, ``orders`` none.

Everything runs in a temporary folder: the repositories are built with ``git``, GitHub's address is
rewritten to that folder for every git call (``url.<folder>.insteadOf``), and GitHub's REST API is
answered by a stand-in. ``git`` required.

Output:

    1. A service's repository
       main, oldest first: Add the graph · Merge pull request #1 from feature · Drop an edge on main · Say more in the README · Break the graph · Mend the graph
    2. The port, GitHub stood in
       key for orders issued to anna: 43 characters, its hash in the config, the key nowhere in it
    3. describe orders
      History orders described for anna
       {'id': 'orders', 'repository': 'acme/service', 'branch': 'main', 'graph_file': 'graph.json', 'versions': 5, 'newest': '…'}
    4. versions of orders, oldest first
      History orders listed for anna
       Add the graph                       214 nodes, 305 edges
       PR #1 Two edges fewer               214 nodes, 303 edges   v1.0 (release Release 1.0)
       Drop an edge on main                214 nodes, 302 edges   v1.1
       Break the graph                     refused: graph 1.1 at nodes/0: matches none of the shapes allowed here
       Mend the graph                      214 nodes, 305 edges
    5. one version's graph
      History orders version read for anna
       PR #1's version: 248,423 bytes, the bytes git holds: True; Cache-Control: public, max-age=31536000, immutable
    6. after the second version
      History orders listed for anna
       Drop an edge on main · Break the graph · Mend the graph
    7. the same read again, naming its ETag
      History orders listed for anna
      History orders listed for anna
       304
    8. one key, one history
      History orders described for anna
       orders with anna's key: 200 · billing with anna's key: 404 {'detail': 'not found'} · orders with no key: 404 {'detail': 'not found'}
    9. guessing keys from one address
       404 ×10, then 429 {'detail': 'too many requests'}
    10. a public repository by a link
      History https://github.com/acme/open/blob/main/graph.json listed for a guest
       no key, no config: 1 version(s), newest Add the graph
    11. a push that changes only billing.json
      History billing listed for bob
      Event push on acme/service changed billing
       webhook: 200 {'changed': ['billing']}
      History billing listed for bob
      History orders listed for anna
       billing: 1 → 2 versions · orders: 5 → 5 versions

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  topic: Maxitor (a graph's history)

Run:
    uv run --extra dev python examples/step_26_maxitor/14_graph_history.py
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from maxitor.repo_graph_port.cli import main as history_command
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.server import create_app

# The repository root: the folder that holds graph-builder.toml, wherever this runs from.
REPO_ROOT = next(path for path in (Path.cwd(), *Path(__file__).resolve().parents) if (path / "graph-builder.toml").is_file())
FRONT_GRAPH = json.loads((REPO_ROOT / "packages/maxitor/front/graph.json").read_text(encoding="utf-8"))
WORK = Path(tempfile.mkdtemp(prefix="graph-history-"))
GITHUB = WORK / "github"


def graph(edges: int | None = None) -> str:
    """Maxitor's own graph as a file holds it, its last edges dropped so that each version differs."""
    document = dict(FRONT_GRAPH)
    if edges is not None:
        document["edges"] = FRONT_GRAPH["edges"][:edges]
    return json.dumps(document, indent=2) + "\n"


def git(repository: Path, *arguments: str) -> str:
    """One git command in ``repository``, with a fixed author."""
    identity = ["-c", "user.name=Example", "-c", "user.email=example@example.com"]
    return subprocess.run(["git", "-C", str(repository), *identity, *arguments], check=True, capture_output=True, text=True).stdout.strip()


def commit(repository: Path, message: str, files: dict[str, str]) -> str:
    """Write ``files``, commit them; the commit."""
    for name, text in files.items():
        (repository / name).write_text(text, encoding="utf-8")
    git(repository, "add", *files)
    git(repository, "commit", "-q", "-m", message)
    return git(repository, "rev-parse", "HEAD")


# GitHub's address is rewritten to WORK/github for every git call this example makes.
os.environ.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"url.{GITHUB.as_uri()}/.insteadOf", "GIT_CONFIG_VALUE_0": "https://github.com/"})

print("1. A service's repository")
service = GITHUB / "acme" / "service.git"
service.mkdir(parents=True)
git(service, "init", "-q", "-b", "main")
first = commit(service, "Add the graph", {"graph.json": graph(), "billing.json": graph(300)})
git(service, "checkout", "-q", "-b", "feature")
commit(service, "Drop two edges", {"graph.json": graph(303)})
git(service, "checkout", "-q", "main")
git(service, "merge", "-q", "--no-ff", "-m", "Merge pull request #1 from feature", "feature")
merged = git(service, "rev-parse", "HEAD")
git(service, "tag", "-a", "v1.0", "-m", "Release 1.0")
direct = commit(service, "Drop an edge on main", {"graph.json": graph(302)})
commit(service, "Say more in the README", {"README.md": "orders and billing\n"})
git(service, "tag", "v1.1")
commit(service, "Break the graph", {"graph.json": json.dumps({"schema_version": "1.1", "nodes": [{"id": 1}], "edges": []})})
commit(service, "Mend the graph", {"graph.json": graph()})
print("   main, oldest first:", " · ".join(git(service, "log", "--first-parent", "--reverse", "--format=%s").splitlines()))

print("2. The port, GitHub stood in")
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
pulls = {merged: [{"number": 1, "title": "Two edges fewer", "body": "", "html_url": "https://github.com/acme/service/pull/1", "merge_commit_sha": merged}]}
releases = {"v1.0": {"name": "Release 1.0", "html_url": "https://github.com/acme/service/releases/tag/v1.0"}}


def stand_in(request: httpx.Request) -> httpx.Response:
    """GitHub's REST API, as much of it as the port asks."""
    path = request.url.path
    if path.startswith("/app/") or path.endswith("/installation"):
        jwt.decode(request.headers["authorization"].removeprefix("Bearer "), private_key.public_key(), algorithms=["RS256"])
        if path.endswith("/access_tokens"):
            return httpx.Response(201, json={"token": "ghs_example", "expires_at": "2099-01-01T00:00:00Z"})
        return httpx.Response(200, json=[{"id": 1}] if path == "/app/installations" else {"id": 1})
    if path.endswith("/pulls"):
        return httpx.Response(200, json=pulls.get(path.split("/")[-2], []))
    release = releases.get(path.rsplit("/", 1)[-1]) if "/releases/tags/" in path else None
    return httpx.Response(200, json=release) if release else httpx.Response(404, json={"message": "Not Found"})


SECRET = "example-webhook-secret"
config = WORK / "histories.toml"
config.write_text(
    '[github]\napp_id = 1\nprivate_key_env = "APP_KEY"\nwebhook_secret_env = "HOOK_SECRET"\n'
    + "".join(
        f'\n[[history]]\nid = "{name}"\nhost = "github"\nrepository = "acme/service"\nbranch = "main"\ngraph_file = "{file}"\n'
        for name, file in (("orders", "graph.json"), ("billing", "billing.json"))
    ),
    encoding="utf-8",
)
key_file = WORK / "key.txt"
# The command prints each key once; the example keeps the keys out of its own output.
with key_file.open("w") as out, contextlib.redirect_stdout(out):
    history_command(["--config", str(config), "key", "new", "--history", "orders", "--name", "anna"])
    history_command(["--config", str(config), "key", "new", "--history", "billing", "--name", "bob"])
anna, bob = key_file.read_text(encoding="utf-8").split()
held = config.read_text(encoding="utf-8")
print(f"   key for orders issued to anna: {len(anna)} characters, its hash in the config, the key nowhere in it"
      if hashlib.sha256(anna.encode()).hexdigest() in held and anna not in held else "   the key is in the config!")
port = TestClient(create_app(config, WORK / "cache", GitHubHost(1, pem, SECRET, transport=httpx.MockTransport(stand_in))))
ANNA = {"X-Maxitor-History-Key": anna}

print("3. describe orders")
described = port.get("/api/v1/history/orders", headers=ANNA).json()
print("  ", {**described, "newest": "…"})

print("4. versions of orders, oldest first")
listed: list[dict[str, Any]] = port.get("/api/v1/history/orders/versions", headers=ANNA).json()["versions"]
for version in listed:
    said = f"PR #{version['pr']['number']} {version['pr']['title']}" if version["pr"] else version["message"]
    size = f"refused: {version['refused']}" if version["refused"] else f"{version['nodes']} nodes, {version['edges']} edges"
    tags = " ".join(f"{t['name']}" + (f" (release {t['release']['title']})" if t["release"] else "") for t in version["tags"])
    print(f"   {said:<35} {size:<22} {tags}".rstrip())

print("5. one version's graph")
answer = port.get(f"/api/v1/history/orders/versions/{merged}", headers=ANNA)
committed = git(service, "show", f"{merged}:graph.json") + "\n"
print(f"   PR #1's version: {len(answer.content):,} bytes, the bytes git holds: {answer.content == committed.encode()};"
      f" Cache-Control: {answer.headers['cache-control']}")

print("6. after the second version")
later = port.get("/api/v1/history/orders/versions", params={"after": merged}, headers=ANNA).json()["versions"]
print("  ", " · ".join(v["message"] or v["pr"]["title"] for v in later))

print("7. the same read again, naming its ETag")
tag = port.get("/api/v1/history/orders/versions", headers=ANNA).headers["etag"]
print("  ", port.get("/api/v1/history/orders/versions", headers={**ANNA, "If-None-Match": tag}).status_code)

print("8. one key, one history")
asks = [("orders with anna's key", "orders", ANNA), ("billing with anna's key", "billing", ANNA), ("orders with no key", "orders", {})]
seen = []
for label, history, headers in asks:
    got = port.get(f"/api/v1/history/{history}", headers=headers)
    seen.append(f"{label}: {got.status_code}" + ("" if got.status_code == 200 else f" {got.json()}"))
print("  ", " · ".join(seen))

print("9. guessing keys from one address")
codes = [port.get("/api/v1/history/orders", headers={"X-Maxitor-History-Key": f"guess-{n}"}) for n in range(11)]
print(f"   404 ×{sum(c.status_code == 404 for c in codes)}, then {codes[-1].status_code} {codes[-1].json()}")

print("10. a public repository by a link")
public = GITHUB / "acme" / "open.git"
public.mkdir(parents=True)
git(public, "init", "-q", "-b", "main")
commit(public, "Add the graph", {"graph.json": graph()})
link = "https://github.com/acme/open/blob/main/graph.json"
opened = port.get("/api/v1/history/public/versions", params={"link": link}).json()["versions"]
print(f"   no key, no config: {len(opened)} version(s), newest {opened[-1]['message']}")

print("11. a push that changes only billing.json")
billing_before = len(port.get("/api/v1/history/billing/versions", headers={"X-Maxitor-History-Key": bob}).json()["versions"])
orders_before = len(listed)
before = git(service, "rev-parse", "HEAD")
after = commit(service, "Bill by the hour", {"billing.json": graph(299)})
event = json.dumps({"ref": "refs/heads/main", "before": before, "after": after, "repository": {"full_name": "acme/service"}}).encode()
signature = "sha256=" + hmac.new(SECRET.encode(), event, hashlib.sha256).hexdigest()
hook = port.post("/api/v1/history/events/github", content=event, headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"})
print(f"   webhook: {hook.status_code} {hook.json()}")
billing_after = len(port.get("/api/v1/history/billing/versions", headers={"X-Maxitor-History-Key": bob}).json()["versions"])
orders_after = len(port.get("/api/v1/history/orders/versions", headers=ANNA).json()["versions"])
print(f"   billing: {billing_before} → {billing_after} versions · orders: {orders_before} → {orders_after} versions")
