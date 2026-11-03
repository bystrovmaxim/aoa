# packages/maxitor/tools/repo_graph_port/tests/test_version_file.py
"""A history joined with its version file: the points, the bad links and the moved folders, on real repositories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from maxitor.repo_graph_port.history import public_history
from maxitor.repo_graph_port.resources.histories_config import load_histories
from maxitor.repo_graph_port.server import create_app

from tests.repo_builder import _Builder, graph
from tests.test_keys import issue

BASE = "/api/v1/history"
TOML = 'kind = "component"\nversion = "{}"\n'


def _reordered(text: str) -> str:
    """The same graph with its top-level nodes in another order."""
    document = json.loads(text)
    document["nodes"].reverse()
    return json.dumps(document, indent=2) + "\n"


class _Service:
    """A repository, and the port reading it as one history."""

    def __init__(self, folder: Path, capsys: pytest.CaptureFixture[str], settings: str = 'version_file = "svc/version.toml"\n') -> None:
        """A first commit with a graph and a version file, and a config naming them."""
        self.builder = _Builder(folder / "repo")
        (folder / "repo" / "svc").mkdir()
        self.folder, self.capsys, self.settings = folder, capsys, settings
        self.sha: dict[str, str] = {}
        self.client: TestClient | None = None
        self.commit("first", {"svc/graph.json": graph(edges=20), "svc/version.toml": TOML.format("1.0.0")})

    def commit(self, name: str, files: dict[str, str]) -> str:
        """Commit ``files`` and remember the commit as ``name``."""
        self.sha[name] = self.builder.commit(name, files)
        return self.sha[name]

    def open(self) -> dict[str, str]:
        """Start the port; the headers that read the history."""
        config = self.folder / "histories.toml"
        config.write_text(
            f'[[history]]\nid = "svc"\nhost = "local"\nrepository = "{self.builder.path}"\nbranch = "main"\ngraph_file = "svc/graph.json"\n{self.settings}',
            encoding="utf-8",
        )
        key = issue(config, self.capsys, "svc", "anna")
        self.client = TestClient(create_app(config, self.folder / "cache"))
        return {"X-Maxitor-History-Key": key}

    def read(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """The history answer and the versions answer."""
        headers = self.open()
        assert self.client is not None
        return self.client.get(f"{BASE}/svc", headers=headers).json(), self.client.get(f"{BASE}/svc/versions", headers=headers).json()


def _row(version: dict[str, Any]) -> tuple[bool, str | None, bool]:
    """A point's three fields."""
    return version["graph_changed"], version["version"], version["version_changed"]


def test_each_point_says_what_changed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Both, only the version, only the graph; a comment, a neutral commit and a reordering make no point."""
    service = _Service(tmp_path, capsys)
    service.commit("both", {"svc/graph.json": graph(edges=21), "svc/version.toml": TOML.format("1.1.0")})
    service.commit("version", {"svc/version.toml": TOML.format("1.1.1")})
    service.commit("graph", {"svc/graph.json": graph(edges=22)})
    service.commit("comment", {"svc/version.toml": "# a note\n" + TOML.format("1.1.1")})
    service.commit("other", {"svc/code.txt": "x"})
    service.commit("order", {"svc/graph.json": _reordered(graph(edges=22))})
    described, listed = service.read()
    assert [v["sha"] for v in listed["versions"]] == [service.sha[name] for name in ("first", "both", "version", "graph")]
    assert [_row(v) for v in listed["versions"]] == [
        (True, "1.0.0", True),
        (True, "1.1.0", True),
        (False, "1.1.1", True),
        (True, "1.1.1", False),
    ]
    assert described["version_file"] == "svc/version.toml" and described["version_problem"] is None and described["versions"] == 4
    assert listed["version_problem"] is None


def test_a_history_with_no_version_file_has_the_points_it_always_had(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Every commit of the graph file is a point, with the neutral values, a reordering among them."""
    service = _Service(tmp_path, capsys, settings="")
    service.commit("version", {"svc/version.toml": TOML.format("1.1.0")})
    service.commit("order", {"svc/graph.json": _reordered(graph(edges=20))})
    described, listed = service.read()
    assert [v["sha"] for v in listed["versions"]] == [service.sha["first"], service.sha["order"]]
    assert {_row(v) for v in listed["versions"]} == {(True, None, False)}
    assert described["version_file"] is None


def test_a_version_only_point_opens_reads_no_graph_and_takes_tags(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Listing stores no copy of the graph; the tag of its version lands on the point, another package's does not; opening it gives the graph in that commit."""
    service = _Service(tmp_path, capsys)
    sha = service.commit("version", {"svc/version.toml": TOML.format("1.1.0")})
    service.builder.git("tag", "svc-v1.1.0")
    service.builder.git("tag", "other-package-v2.0.0")
    headers = service.open()
    assert service.client is not None
    listed = service.client.get(f"{BASE}/svc/versions", headers=headers).json()["versions"]
    assert [tag["name"] for tag in listed[-1]["tags"]] == ["svc-v1.1.0"]
    assert listed[-1]["nodes"] == listed[0]["nodes"] and listed[-1]["change"]["links"] == {"added": 0, "removed": 0}
    assert not list((tmp_path / "cache").rglob(f"{sha}.graph"))
    opened = service.client.get(f"{BASE}/svc/versions/{sha}", headers=headers)
    assert opened.status_code == 200 and opened.content == graph(edges=20).encode("utf-8")


def test_the_unusual_cases_of_a_number(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A broken file, its fix with the same number, a number going down, a deletion, a restored graph."""
    service = _Service(tmp_path, capsys)
    service.commit("broken", {"svc/version.toml": "version = "})
    service.commit("broken and graph", {"svc/graph.json": graph(edges=21)})
    service.commit("fixed", {"svc/version.toml": TOML.format("1.0.0")})
    service.commit("down", {"svc/version.toml": TOML.format("0.9.0")})
    _, listed = service.read()
    assert [v["sha"] for v in listed["versions"]] == [service.sha[name] for name in ("first", "broken and graph", "down")]
    assert [_row(v) for v in listed["versions"]] == [(True, "1.0.0", True), (True, None, False), (False, "0.9.0", True)]


def test_a_version_file_later_than_the_graph(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Earlier points have no number; the first readable number is a change."""
    service = _Service(tmp_path, capsys, settings='version_file = "svc/late.toml"\n')
    service.commit("graph", {"svc/graph.json": graph(edges=21)})
    service.commit("late", {"svc/late.toml": TOML.format("2.0.0")})
    _, listed = service.read()
    assert [_row(v) for v in listed["versions"]] == [(True, None, False), (True, None, False), (False, "2.0.0", True)]


def test_a_deleted_graph_is_a_point_and_restoring_it_is_the_next(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The deletion shows ``refused``, as it always did."""
    service = _Service(tmp_path, capsys)
    service.builder.git("rm", "-q", "svc/graph.json")
    service.builder.git("commit", "-q", "-m", "gone")
    service.commit("back", {"svc/graph.json": graph(edges=20)})
    _, listed = service.read()
    assert len(listed["versions"]) == 3 and listed["versions"][1]["refused"] == "the commit removed the graph file"
    assert listed["versions"][2]["graph_changed"] is True and listed["versions"][2]["refused"] is None


def test_a_package_file_and_a_key_ignore_a_change_of_dependencies(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A dependency in ``pyproject.toml`` makes no point; the number does."""
    service = _Service(tmp_path, capsys, settings='version_file = "pyproject.toml"\nversion_key = "project.version"\n')
    service.commit("number", {"pyproject.toml": '[project]\nversion = "3.0.0"\n'})
    service.commit("dependency", {"pyproject.toml": '[project]\nversion = "3.0.0"\ndependencies = ["x"]\n'})
    service.commit("raised", {"pyproject.toml": '[project]\nversion = "3.1.0"\n'})
    _, listed = service.read()
    assert [v["sha"] for v in listed["versions"]] == [service.sha[name] for name in ("first", "number", "raised")]
    assert listed["versions"][-1]["version"] == "3.1.0"


@pytest.mark.parametrize(
    ("settings", "files", "said"),
    [
        ('version_file = "other/version.toml"\n', {}, "is not in a folder above"),
        ('version_file = "svc/gone.toml"\n', {}, "svc/gone.toml is not on main"),
        ('version_file = "svc/version.toml"\nversion_key = "absent"\n', {}, "has no absent"),
        ('version_file = "svc/version.toml"\n', {"svc/version.toml": "version = 3\n"}, "not a written number"),
        ('version_file = "svc/version.toml"\n', {"svc/version.toml": "version = "}, "cannot be read"),
        ('version_file = "svc/pom.xml"\n', {"svc/pom.xml": "<project/>"}, "neither TOML nor JSON"),
        ('version_file = "svc/version.toml"\n', {"svc/version.toml": 'kind = "package"\ndriver = "python"\n'}, "names a driver"),
    ],
)
def test_a_bad_link_is_explained_in_both_answers_and_the_graph_opens(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], settings: str, files: dict[str, str], said: str
) -> None:
    """Each cause, in the history answer and the versions answer."""
    service = _Service(tmp_path, capsys, settings=settings)
    if files:
        service.commit("bad", files)
    headers = service.open()
    assert service.client is not None
    described = service.client.get(f"{BASE}/svc", headers=headers).json()
    answer = service.client.get(f"{BASE}/svc/versions", headers=headers)
    assert said in described["version_problem"] and said in answer.json()["version_problem"]
    sha = answer.json()["versions"][0]["sha"]
    assert service.client.get(f"{BASE}/svc/versions/{sha}", headers=headers).status_code == 200


def test_a_wrong_path_does_not_refuse_the_config_but_a_wrong_type_does(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A wrong type is a mistake in the file itself."""
    config = tmp_path / "histories.toml"
    entry = '[[history]]\nid = "a"\nhost = "local"\nrepository = "/r"\nbranch = "main"\ngraph_file = "g.json"\n'
    config.write_text(entry + 'version_file = "nowhere/at/all.toml"\n', encoding="utf-8")
    assert load_histories(config)
    config.write_text(entry + "graph_file_before = 3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="graph_file_before"):
        load_histories(config)


def test_a_version_link_elsewhere_is_a_problem() -> None:
    """Another repository or branch cannot name this history's version."""
    link = "https://github.com/o/r/blob/main/svc/graph.json"
    history = public_history(link, "https://github.com/o/other/blob/main/svc/version.toml", "version")
    assert history is not None and history.version_file is None and "o/r on main" in str(history.version_refused)
    same = public_history(link, "https://github.com/o/r/blob/main/pyproject.toml", "project.version")
    assert same is not None and same.version_file == "pyproject.toml" and same.version_key == "project.version"


def test_a_moved_folder_keeps_its_history(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With old paths listed both sides of the move are read, and without them too: the port finds them in git."""
    service = _Service(tmp_path, capsys, settings='version_file = "new/version.toml"\ngraph_file_before = ["svc/graph.json"]\nversion_file_before = ["svc/version.toml"]\n')
    service.commit("raised", {"svc/version.toml": TOML.format("1.1.0")})
    (tmp_path / "repo" / "new").mkdir()
    service.commit("moved", {"new/graph.json": graph(edges=20), "new/version.toml": TOML.format("1.1.0")})
    service.builder.git("rm", "-q", "svc/graph.json", "svc/version.toml")
    service.builder.git("commit", "-q", "--amend", "-m", "moved")
    service.commit("after", {"new/version.toml": TOML.format("1.2.0")})
    config = tmp_path / "histories.toml"
    headers = service.open()
    text = config.read_text(encoding="utf-8").replace('graph_file = "svc/graph.json"', 'graph_file = "new/graph.json"')
    config.write_text(text, encoding="utf-8")
    client = TestClient(create_app(config, tmp_path / "cache-new"))
    listed = client.get(f"{BASE}/svc/versions", headers=headers).json()
    assert [v["version"] for v in listed["versions"]] == ["1.0.0", "1.1.0", "1.2.0"]
    assert listed["version_problem"] is None
    bare = text.replace('graph_file_before = ["svc/graph.json"]\n', "").replace('version_file_before = ["svc/version.toml"]\n', "")
    config.write_text(bare, encoding="utf-8")
    fresh = TestClient(create_app(config, tmp_path / "cache-bare"))
    assert [v["version"] for v in fresh.get(f"{BASE}/svc/versions", headers=headers).json()["versions"]] == ["1.0.0", "1.1.0", "1.2.0"]


def _propose(service: _Service, number: int, name: str, files: dict[str, str]) -> str:
    """An open pull request: a branch off ``main`` with one commit, kept as ``refs/pull/<number>/head``."""
    builder = service.builder
    builder.git("checkout", "-q", "-b", f"proposal-{number}", "main")
    head = builder.commit(name, files)
    builder.git("checkout", "-q", "main")
    builder.git("update-ref", f"refs/pull/{number}/head", head)
    return head


def test_an_open_pull_request_that_raises_only_the_version_is_listed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A proposal that raises the number is listed as a small point; one that changes neither file is not."""
    service = _Service(tmp_path, capsys)
    service.commit("both", {"svc/graph.json": graph(edges=21), "svc/version.toml": TOML.format("1.1.0")})
    raised = _propose(service, 7, "version only", {"svc/version.toml": TOML.format("1.1.1"), "svc/code.txt": "y"})
    _propose(service, 8, "code only", {"svc/code.txt": "z"})
    _, listed = service.read()
    assert [(p["sha"], p["pr"]["number"]) for p in listed["proposals"]] == [(raised, 7)]
    assert _row(listed["proposals"][0]) == (False, "1.1.1", True)
