# packages/maxitor/tools/repo_graph_port/tests/repo_builder.py
"""A git repository built in a temporary folder, shaped so that every rule of a history has a case."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"
GRAPH_FILE = "graph.json"


@dataclass
class BuiltRepository:
    """The repository and the commits a test names: ``sha[name]``; ``versions`` are what a history must list."""

    path: Path
    sha: dict[str, str] = field(default_factory=dict)
    versions: list[str] = field(default_factory=list)


class _Builder:
    """Commits with fixed authors and dates, so every run builds the same history."""

    def __init__(self, path: Path) -> None:
        """Start an empty repository on ``main``."""
        self.path = path
        self.clock = 0
        path.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")

    def git(self, *arguments: str) -> str:
        """Run git in the repository with a fixed identity and the next date (UTC+03:00)."""
        self.clock += 1
        date = f"2026-10-01T{self.clock // 60:02d}:{self.clock % 60:02d}:00+03:00"
        identity = {"GIT_AUTHOR_NAME": "Tester", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "Tester",
                    "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        done = subprocess.run(["git", "-C", str(self.path), *arguments], check=True, capture_output=True, text=True,
                              env={**os.environ, **identity})
        return done.stdout.strip()

    def commit(self, message: str, files: dict[str, str]) -> str:
        """Write ``files`` and commit them; return the commit."""
        for name, text in files.items():
            (self.path / name).write_text(text, encoding="utf-8")
        self.git("add", "--", *files)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def merge(self, branch: str, message: str) -> str:
        """Merge ``branch`` into ``main`` with a merge commit; return it."""
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", message, branch)
        return self.git("rev-parse", "HEAD")


def graph(version: str = "1.1", edges: int | None = None) -> str:
    """A valid graph of ``version``, its last edges dropped to make it differ; the text a file holds."""
    document: dict[str, Any] = json.loads((FIXTURES / f"graph-{version}.json").read_text(encoding="utf-8"))
    if edges is not None:
        document["edges"] = document["edges"][:edges]
    return json.dumps(document, indent=2) + "\n"


def build_repository(path: Path) -> BuiltRepository:
    """
    The history every rule is tested on, oldest first on ``main``:

    ``pre`` README only (tag ``pre``) · ``v1`` adds the graph · ``readme`` README only · ``a1``, ``a2`` on a branch,
    merged as ``m1`` (tag ``v1.0``, annotated) · ``d1`` straight on ``main`` · ``m2`` merges a branch that touched
    only the README (tag ``v1.1`` on it) · ``c1`` on a branch (tag ``side``), merged as ``m3`` · ``bad`` a graph its
    schema refuses · ``old`` a ``1.0`` graph. Versions: ``v1``, ``m1``, ``d1``, ``m3``, ``bad``, ``old``.
    """
    b = _Builder(path)
    built = BuiltRepository(path)
    sha = built.sha
    sha["pre"] = b.commit("Start with a README", {"README.md": "a service\n"})
    b.git("tag", "pre", sha["pre"])
    sha["v1"] = b.commit("Add the graph", {GRAPH_FILE: graph(edges=28)})
    sha["readme"] = b.commit("Say more in the README", {"README.md": "a service, described\n"})
    b.git("checkout", "-q", "-b", "feature-a")
    sha["a1"] = b.commit("Drop one edge", {GRAPH_FILE: graph(edges=27)})
    sha["a2"] = b.commit("Drop another edge", {GRAPH_FILE: graph(edges=26)})
    sha["m1"] = b.merge("feature-a", "Merge pull request #1 from feature-a\n\nTwo edges fewer")
    b.git("tag", "-a", "v1.0", "-m", "Release 1.0", sha["m1"])
    sha["d1"] = b.commit("Drop an edge on main", {GRAPH_FILE: graph(edges=25)})
    b.git("checkout", "-q", "-b", "feature-b")
    b.commit("README on a branch", {"README.md": "a service, described again\n"})
    sha["m2"] = b.merge("feature-b", "Merge pull request #2 from feature-b")
    b.git("tag", "v1.1", sha["m2"])
    b.git("checkout", "-q", "-b", "feature-c")
    sha["c1"] = b.commit("Drop an edge on a side branch", {GRAPH_FILE: graph(edges=24)})
    b.git("tag", "side", sha["c1"])
    sha["m3"] = b.merge("feature-c", "Merge pull request #3 from feature-c")
    sha["bad"] = b.commit("Break the graph", {GRAPH_FILE: json.dumps({"schema_version": "1.1", "nodes": [{"id": 1}], "edges": []})})
    sha["old"] = b.commit("Go back to a 1.0 graph", {GRAPH_FILE: graph(version="1.0")})
    built.versions = [sha[name] for name in ("v1", "m1", "d1", "m3", "bad", "old")]
    return built


def add_version(built: BuiltRepository, edges: int) -> str:
    """One more commit on ``main`` that changes the graph; return it."""
    b = _Builder.__new__(_Builder)
    b.path, b.clock = built.path, 500
    return b.commit("One more version", {GRAPH_FILE: graph(edges=edges)})
