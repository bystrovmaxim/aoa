"""
22_version_file.py — a graph's history joined with its version file

A graph belongs to a level with its own version number: a component, or a whole package. A history can name the
file that holds that number. Then the port lists the commits that changed either file, and each point says three
things: whether the graph changed, which version is there, and whether that version changed. A commit that changed
neither, in substance, is no point at all. This example runs a real port over a small repository.

The cases, with the real output at the bottom:

  1. the points of a history with a version file;
  2. the same repository with no version file: the points it always had;
  3. a package's file and a key: a dependency makes no point, a number does;
  4. each bad link: explained in plain words, and the graph still opens;
  5. a moved folder: old paths keep the history before the move.

Everything runs in a temporary folder; ``git`` required.

Output:

    1. The points of a history with a version file
      History svc listed for anna
       first            graph changed  1.0.0  new
       model and number graph changed  1.1.0  new
       code, number     same graph     1.1.1  new
       model only       graph changed  1.1.1
    2. No version file: the points it always had
      History svc listed for anna
       first            graph changed  —
       model and number graph changed  —
       model only       graph changed  —
       nodes reordered  graph changed  —
    3. A package's file and a key
      History svc listed for anna
       first            graph changed  3.0.0  new
       raised           same graph     3.1.0  new
    4. Each bad link
      History svc listed for anna
       other/version.toml is not in a folder above svc/graph.json (1 version, the graph opens)
      History svc listed for anna
       svc/gone.toml is not on main (1 version, the graph opens)
      History svc listed for anna
       svc/pom.xml is neither TOML nor JSON; link a component's version.toml, or use no version file (1 version, the graph opens)
      History svc listed for anna
       svc/version.toml names a driver and holds no number; link the file the driver reads, with its key (1 version, the graph opens)
    5. A moved folder
      History svc listed for anna
       first            graph changed  1.0.0  new
       moved            same graph     1.1.0  new
       without the old paths:
      History svc listed for anna
       moved            graph changed  1.1.0  new
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from maxitor.repo_graph_port.cli import main as port_cli
from maxitor.repo_graph_port.server import create_app

BASE = "/api/v1/history"
FOLDER = Path(tempfile.mkdtemp())


def graph(entities: int, order: int = 1) -> str:
    """A valid graph of ``entities`` nodes, in the given order."""
    nodes = [{"id": f"shop.E{n}", "type": "Entity", "label": f"E{n}", "properties": {}} for n in range(entities)][::order]
    return json.dumps({"schema_version": "1.2", "nodes": nodes, "edges": []}, indent=2) + "\n"


def component(number: str) -> str:
    """A component's ``version.toml``."""
    return f'kind = "component"\nversion = "{number}"\n'


class Repository:
    """A git repository the example commits to."""

    def __init__(self, name: str) -> None:
        """Start it, with the folder ``svc``."""
        self.path = FOLDER / name
        (self.path / "svc").mkdir(parents=True)
        self.git("init", "-q", "-b", "main")

    def git(self, *arguments: str) -> None:
        """Run git in the repository."""
        subprocess.run(["git", "-C", str(self.path), "-c", "user.name=T", "-c", "user.email=t@e", *arguments], check=True, capture_output=True)

    def commit(self, message: str, files: dict[str, str]) -> None:
        """Write ``files`` and commit them."""
        for name, text in files.items():
            (self.path / name).parent.mkdir(parents=True, exist_ok=True)
            (self.path / name).write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)


def read(repository: Repository, settings: str, graph_file: str = "svc/graph.json") -> list[dict[str, Any]] | dict[str, Any]:
    """The versions answer of a port started over ``repository`` with ``settings``."""
    config = repository.path.parent / f"{repository.path.name}-{abs(hash(settings))}.toml"
    config.write_text(
        f'[[history]]\nid = "svc"\nhost = "local"\nrepository = "{repository.path}"\nbranch = "main"\ngraph_file = "{graph_file}"\n{settings}',
        encoding="utf-8",
    )
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        port_cli(["--config", str(config), "key", "new", "--history", "svc", "--name", "anna"])
    client = TestClient(create_app(config, config.with_suffix(".cache")))
    answer: dict[str, Any] = client.get(f"{BASE}/svc/versions", headers={"X-Maxitor-History-Key": out.getvalue().strip()}).json()
    return answer


def show(answer: Any) -> None:
    """One line per point."""
    for point in answer["versions"]:
        graph_word = "graph changed" if point["graph_changed"] else "same graph   "
        version = f'{point["version"] or "—":6} {"new" if point["version_changed"] else "   "}'
        print(f'   {point["message"].strip().ljust(16)} {graph_word}  {version}')


def main() -> None:
    """Walk the five cases."""
    print("1. The points of a history with a version file")
    service = Repository("service")
    service.commit("first", {"svc/graph.json": graph(2), "svc/version.toml": component("1.0.0")})
    service.commit("model and number", {"svc/graph.json": graph(3), "svc/version.toml": component("1.1.0")})
    service.commit("code, number", {"svc/code.txt": "x", "svc/version.toml": component("1.1.1")})
    service.commit("model only", {"svc/graph.json": graph(4)})
    service.commit("a comment", {"svc/version.toml": "# a note\n" + component("1.1.1")})
    service.commit("nodes reordered", {"svc/graph.json": graph(4, -1)})
    show(read(service, 'version_file = "svc/version.toml"\n'))

    print("2. No version file: the points it always had")
    show(read(service, ""))

    print("3. A package's file and a key")
    package = Repository("package")
    package.commit("first", {"svc/graph.json": graph(2), "pyproject.toml": '[project]\nversion = "3.0.0"\n'})
    package.commit("a dependency", {"pyproject.toml": '[project]\nversion = "3.0.0"\ndependencies = ["x"]\n'})
    package.commit("raised", {"pyproject.toml": '[project]\nversion = "3.1.0"\n'})
    show(read(package, 'version_file = "pyproject.toml"\nversion_key = "project.version"\n'))

    print("4. Each bad link")
    bad = Repository("bad")
    bad.commit("first", {"svc/graph.json": graph(2), "svc/version.toml": 'kind = "package"\ndriver = "python"\n', "svc/pom.xml": "<project/>", "other/version.toml": component("1.0.0")})
    for settings in (
        'version_file = "other/version.toml"\n',
        'version_file = "svc/gone.toml"\n',
        'version_file = "svc/pom.xml"\n',
        'version_file = "svc/version.toml"\n',
    ):
        answer = read(bad, settings)
        print(f'   {answer["version_problem"]} ({len(answer["versions"])} version, the graph opens)')

    print("5. A moved folder")
    moved = Repository("moved")
    moved.commit("first", {"svc/graph.json": graph(2), "svc/version.toml": component("1.0.0")})
    moved.git("mv", "svc", "new")
    moved.commit("moved", {"new/version.toml": component("1.1.0")})
    show(read(moved, 'version_file = "new/version.toml"\ngraph_file_before = ["svc/graph.json"]\nversion_file_before = ["svc/version.toml"]\n', "new/graph.json"))
    print("   without the old paths:")
    show(read(moved, 'version_file = "new/version.toml"\n', "new/graph.json"))


if __name__ == "__main__":
    main()
