# packages/maxitor/tools/repo_graph_port/tests/test_moved_files.py
"""A graph file and its version file followed through a move, on real repositories (spec 057, FR-003, FR-004)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from maxitor.repo_graph_port.history import History
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.server import create_app

from tests.repo_builder import _Builder, graph
from tests.stand_in_github import StandInGitHub
from tests.test_keys import config_file

BASE = "/api/v1/history"
TOML = 'kind = "component"\nversion = "{}"\n'


def _moved_in_a_pull_request(path: Path) -> _Builder:
    """Three versions at ``a/``, then ``a/`` moved to ``b/`` on a branch merged into ``main``, then one more at ``b/``."""
    builder = _Builder(path)
    (path / "a").mkdir()
    for n, version in enumerate(("1.0.0", "1.1.0", "1.2.0")):
        builder.commit(f"v{n}", {"a/graph.json": graph(edges=20 + n), "a/version.toml": TOML.format(version)})
    builder.git("checkout", "-q", "-b", "move")
    builder.git("mv", "a", "b")
    builder.git("commit", "-q", "-m", "move")
    builder.merge("move", "Merge pull request #7 from move")
    builder.commit("after", {"b/graph.json": graph(edges=23), "b/version.toml": TOML.format("1.3.0")})
    return builder


def _versions(tmp_path: Path, link: str) -> TestClient:
    """The port with no history of ``link`` in its config: it reads the link as a public history."""
    return TestClient(create_app(config_file(tmp_path), tmp_path / "cache", GitHubHost(transport=StandInGitHub(None).transport())))


LINK = "https://github.com/owner/service/blob/main/b/graph.json"
VERSION_LINK = "https://github.com/owner/service/blob/main/b/version.toml"


def test_a_mirror_names_the_paths_a_file_had(tmp_path: Path) -> None:
    """FR-003: a move merged as a pull request is found on the first-parent line; a file that never moved has none."""
    builder = _moved_in_a_pull_request(tmp_path / "repo")
    mirror = GitMirror(tmp_path / "mirrors")
    mirror.open(str(builder.path))
    assert mirror.earlier_paths(str(builder.path), "main", "b/graph.json") == ["a/graph.json"]
    assert mirror.earlier_paths(str(builder.path), "main", "b/version.toml") == ["a/version.toml"]
    builder.commit("readme", {"README.md": "x\\n"})
    assert mirror.earlier_paths(str(builder.path), "main", "README.md") == []


def test_a_file_moved_twice_names_both_paths_newest_first(tmp_path: Path) -> None:
    """FR-003: every earlier path, the latest move first."""
    builder = _moved_in_a_pull_request(tmp_path / "repo")
    builder.git("mv", "b", "c")
    builder.git("commit", "-q", "-m", "again")
    mirror = GitMirror(tmp_path / "mirrors")
    mirror.open(str(builder.path))
    assert mirror.earlier_paths(str(builder.path), "main", "c/graph.json") == ["b/graph.json", "a/graph.json"]


def test_found_and_listed_paths_are_joined_once() -> None:
    """FR-004: the paths git found, then the ones the config lists, none twice and never the current one."""
    history = History(id="svc", host="local", repository="r", branch="main", graph_file="c/graph.json", graph_file_before=("a/graph.json", "old/graph.json"))
    followed = history.followed(["b/graph.json", "a/graph.json", "c/graph.json"], [])
    assert followed.graph_paths == ("c/graph.json", "b/graph.json", "a/graph.json", "old/graph.json")
    assert followed.version_paths == ()


def test_a_public_history_lists_its_versions_before_the_move_each_read_at_its_path(tmp_path: Path, github_in: Path) -> None:
    """US2: a link to the new path lists the versions before the move and after it, oldest first, each number and each graph read where it was."""
    _moved_in_a_pull_request(github_in / "owner" / "service.git")
    client = _versions(tmp_path, LINK)
    query = {"link": LINK, "version_link": VERSION_LINK}
    listed = client.get(f"{BASE}/public/versions", params=query).json()
    assert [v["version"] for v in listed["versions"]] == ["1.0.0", "1.1.0", "1.2.0", "1.3.0"]
    assert listed["version_problem"] is None
    first = listed["versions"][0]["sha"]
    assert client.get(f"{BASE}/public/versions/{first}", params=query).content == graph(edges=20).encode("utf-8")


def test_a_file_rewritten_beyond_recognition_starts_its_history_at_the_move(tmp_path: Path, github_in: Path) -> None:
    """Edge case: what git cannot see as a move is not followed; the history starts where the new file did."""
    builder = _Builder(github_in / "owner" / "service.git")
    (builder.path / "a").mkdir()
    builder.commit("v0", {"a/graph.json": graph(edges=20)})
    builder.commit("v1", {"a/graph.json": graph(edges=21)})
    (builder.path / "b").mkdir()
    builder.git("rm", "-q", "-r", "a")
    rewritten = builder.commit("rewritten", {"b/graph.json": '{"schema_version": "1.3", "nodes": [], "edges": []}\n'})
    versions = _versions(tmp_path, LINK).get(f"{BASE}/public/versions", params={"link": LINK}).json()["versions"]
    assert [v["sha"] for v in versions] == [rewritten]
