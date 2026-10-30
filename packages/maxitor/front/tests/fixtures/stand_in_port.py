# packages/maxitor/front/tests/fixtures/stand_in_port.py
"""
A stand-in repo-graph-port: histories for every mode, served over real HTTP on a free local port.

Maxitor reads a history only through a port (spec 037, FR-003), and the front never imports
the port's code (``scripts/package_boundaries.toml``), so tests stand the port in by its
contract (specs/036-repo-graph-port/contracts/actions.md, specs/037-history-one-version/contracts/port.md):
``describe``, ``versions`` with ``ETag``/``304``, ``version`` as the graph file's bytes, the
``public`` routes by ``link``, ``404`` for any refusal and ``429`` once a client sent too many
wrong keys. It also serves a running service — the Live of the histories that have one — and
remembers every request line and header it received, so a test can look for a key in them.

Histories (``HISTORIES``): ``two`` — M2, three versions, the middle one refused; ``one`` — M3;
``live`` — M4; ``live-one`` — M5; ``live-empty`` — M6; ``empty`` — M7; and a public link (M2).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

_FRONT = Path(__file__).resolve().parents[2]
#: Two real graph files of different sizes: Maxitor's own and the port's.
GRAPH_A = (_FRONT / "graph.json").read_bytes()
GRAPH_B = (_FRONT.parent / "tools" / "repo_graph_port" / "graph.json").read_bytes()
#: The public link the stand-in serves as a history.
PUBLIC_LINK = "https://github.com/owner/service/blob/main/graph.json"


def counts(graph: bytes) -> tuple[int, int]:
    """The node and edge counts of a graph file."""
    document = json.loads(graph)
    return len(document["nodes"]), len(document["edges"])


def version(number: int, graph: bytes, *, refused: str | None = None, release: str | None = None) -> dict[str, Any]:
    """A version as the port lists it, made by pull request ``number``."""
    nodes, edges = counts(graph)
    entry: dict[str, Any] = {
        "sha": hashlib.sha1(f"{number}".encode()).hexdigest(),
        "date": f"2026-10-{number:02d}T12:00:00+00:00",
        "pr": {"number": number, "title": f"Change {number}", "body": f"What change {number} did.\n\nhttps://example.com/{number} and #{number}", "url": f"https://github.com/owner/service/pull/{number}"},
        "tags": [{"name": release, "release": {"title": release, "url": f"https://github.com/owner/service/releases/{release}"}}] if release else [],
        "nodes": nodes,
        "edges": edges,
    }
    if refused:
        entry["refused"] = refused
    return entry


@dataclass
class StandInHistory:
    """One history the stand-in serves: its key, its Live, its versions and their graphs."""

    key: str
    versions: list[dict[str, Any]]
    graphs: dict[str, bytes]
    live: str | None = None
    more_keys: list[str] = field(default_factory=list)
    proposals: list[dict[str, Any]] = field(default_factory=list)

    def opens(self, key: str) -> bool:
        """Whether ``key`` opens this history."""
        return any(secrets.compare_digest(key, known) for known in [self.key, *self.more_keys])


@dataclass
class StandInPort:
    """The stand-in's state, which tests change between requests."""

    histories: dict[str, StandInHistory]
    public: StandInHistory
    base: str = ""
    live_body: bytes = b""
    block_after: int = 10
    wrong: int = 0
    requests: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)

    def address(self, history: str) -> str:
        """A private history's address, key included, as a user pastes it."""
        return f"{self.base}/api/v1/history/{history}#key={self.histories[history].key}"

    def name(self, history: str) -> str:
        """A private history's name: its address without the key."""
        return f"{self.base}/api/v1/history/{history}"

    def keys(self) -> list[str]:
        """Every key the stand-in knows."""
        return [history.key for history in self.histories.values()]


def _histories(live: str) -> tuple[dict[str, StandInHistory], StandInHistory]:
    """The histories of every mode."""
    three = [version(1, GRAPH_B, release="v0.1.0"), version(2, GRAPH_A, refused="nodes[3]: 'id' is a required property"), version(3, GRAPH_A)]
    graphs = {three[0]["sha"]: GRAPH_B, three[1]["sha"]: GRAPH_A, three[2]["sha"]: GRAPH_A}
    single = [version(4, GRAPH_B)]

    def made(versions: list[dict[str, Any]], with_live: bool) -> StandInHistory:
        return StandInHistory(
            key=secrets.token_urlsafe(32),
            versions=list(versions),
            graphs={v["sha"]: graphs.get(v["sha"], GRAPH_B) for v in versions},
            live=live if with_live else None,
        )

    histories = {
        "two": made(three, False),
        "one": made(single, False),
        "live": made(three, True),
        "live-one": made(single, True),
        "live-empty": made([], True),
        "empty": made([], False),
    }
    return histories, made(three, False)


def _handler(port: StandInPort) -> type[BaseHTTPRequestHandler]:
    """The request handler over ``port``'s state."""

    class Handler(BaseHTTPRequestHandler):
        """Answers the port's routes and the Live service."""

        def do_GET(self) -> None:
            """Route one request."""
            port.requests.append(self.path)
            port.headers.append(" ".join(f"{k}: {v}" for k, v in self.headers.items()))
            parts = urlsplit(self.path)
            if parts.path == "/live/graph-json":
                self._send(200, port.live_body)
                return
            segments = parts.path.removeprefix("/api/v1/history/").split("/")
            if segments[0] == "public":
                links = parse_qs(parts.query).get("link", [])
                history = port.public if links == [PUBLIC_LINK] else None
            else:
                found = port.histories.get(segments[0])
                key = self.headers.get("X-Maxitor-History-Key", "")
                history = found if found is not None and found.opens(key) else None
                if history is None:
                    port.wrong += 1
                    if port.wrong > port.block_after:
                        self._send(429, b'{"detail": "too many requests"}')
                        return
            if history is None:
                self._send(404, b'{"detail": "not found"}')
                return
            self._answer(history, segments[0], segments[1:])

        def _answer(self, history: StandInHistory, name: str, rest: list[str]) -> None:
            """Answer describe, versions or one version of ``history``."""
            if not rest:
                body = {"id": name, "repository": "owner/service", "branch": "main", "graph_file": "graph.json", "versions": len(history.versions), "newest": history.versions[-1]["sha"] if history.versions else None}
                if name != "public":
                    body.update(live=history.live, reader="anna")
                self._send(200, json.dumps(body).encode())
            elif rest == ["versions"]:
                payload = json.dumps({"versions": history.versions, "proposals": history.proposals}).encode()
                etag = '"' + hashlib.sha256(payload).hexdigest()[:16] + '"'
                if self.headers.get("If-None-Match") == etag:
                    self._send(304, b"", {"ETag": etag})
                else:
                    self._send(200, payload, {"ETag": etag})
            elif len(rest) == 2 and rest[0] == "versions" and rest[1] in history.graphs:
                self._send(200, history.graphs[rest[1]], {"Cache-Control": "public, max-age=31536000, immutable"})
            else:
                self._send(404, b'{"detail": "not found"}')

        def _send(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
            """Send one answer."""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            """Keep the test output quiet."""

    return Handler


@contextmanager
def stand_in_port() -> Iterator[StandInPort]:
    """Serve the stand-in on a free local port for the block's duration."""
    port = StandInPort(histories={}, public=StandInHistory(key="", versions=[], graphs={}))
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(port))
    port.base = f"http://127.0.0.1:{server.server_address[1]}"
    port.histories, port.public = _histories(f"{port.base}/live/graph-json")
    port.live_body = GRAPH_A
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield port
    finally:
        server.shutdown()
