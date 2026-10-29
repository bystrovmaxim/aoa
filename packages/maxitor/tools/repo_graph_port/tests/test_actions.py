# packages/maxitor/tools/repo_graph_port/tests/test_actions.py
"""``describe``, ``history`` and ``version`` on the shaped repository: their answers, ``after``, the cache, the fallback fetch."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from maxitor.repo_graph_port.actions.describe_history_action import DescribeHistoryAction, DescribeHistoryParams
from maxitor.repo_graph_port.actions.history_action import HistoryAction, HistoryParams
from maxitor.repo_graph_port.actions.version_action import VersionAction, VersionParams
from maxitor.repo_graph_port.commit import Commit
from maxitor.repo_graph_port.history_context import HistoryContext
from maxitor.repo_graph_port.history_not_found_error import HistoryNotFoundError
from maxitor.repo_graph_port.history_reader_info import HistoryReaderInfo
from maxitor.repo_graph_port.history_reader_role import HistoryReaderRole
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.resources.version_cache import VersionCache
from maxitor.repo_graph_port.tag import Tag

from aoa.action_machine.context import env
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from tests.repo_builder import GRAPH_FILE, BuiltRepository, build_repository, graph


class CountingMirror(GitMirror):
    """The real mirror, counting every git read it is asked for."""

    def __init__(self, cache: Path) -> None:
        """A mirror whose calls are counted by name."""
        super().__init__(cache)
        self.calls: Counter[str] = Counter()

    def open(self, repository: str, url: str | None = None, auth: Mapping[str, str] | None = None) -> None:
        """Count, then open."""
        self.calls["open"] += 1
        super().open(repository, url, auth)

    def fetch(self, repository: str, auth: Mapping[str, str] | None = None) -> None:
        """Count, then fetch."""
        self.calls["fetch"] += 1
        super().fetch(repository, auth)

    def versions(self, repository: str, branch: str, path: str) -> list[Commit]:
        """Count, then list."""
        self.calls["versions"] += 1
        return super().versions(repository, branch, path)

    def first_parents(self, repository: str, branch: str) -> list[str]:
        """Count, then list."""
        self.calls["first_parents"] += 1
        return super().first_parents(repository, branch)

    def tags(self, repository: str) -> list[Tag]:
        """Count, then list."""
        self.calls["tags"] += 1
        return super().tags(repository)

    def file_at(self, repository: str, sha: str, path: str, auth: Mapping[str, str] | None = None) -> bytes | None:
        """Count, then read."""
        self.calls["file_at"] += 1
        return super().file_at(repository, sha, path, auth)


@env("history_refresh_seconds", 0)
class AlwaysFetch(HistoryContext):
    """A context whose fallback interval has always passed."""


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> BuiltRepository:
    """The shaped repository, built once for the module."""
    return build_repository(tmp_path_factory.mktemp("history") / "service")


class Server:
    """One machine and the connections every history action is given."""

    def __init__(self, built: BuiltRepository, folder: Path) -> None:
        """A config naming the built repository as history ``service``, a counting mirror, a cache."""
        config = folder / "histories.toml"
        config.write_text(
            f'[[history]]\nid = "service"\nhost = "local"\nrepository = "{built.path}"\nbranch = "main"\ngraph_file = "{GRAPH_FILE}"\n',
            encoding="utf-8",
        )
        self.machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
        self.mirror = CountingMirror(folder / "cache")
        self.connections: dict[str, Any] = {
            "HistoriesConfig": HistoriesConfig(config),
            "GitMirror": self.mirror,
            "VersionCache": VersionCache(folder / "cache"),
        }

    async def run(self, action: Any, params: Any, context: type[HistoryContext] = HistoryContext) -> Any:
        """Run one action as the holder of a key to ``service``, in a context of class ``context``."""
        reader = HistoryReaderInfo(user_id="tester", roles=(HistoryReaderRole,), history="service")
        return await self.machine.run(context(user=reader), action, params, self.connections)


@pytest.fixture
def server(built: BuiltRepository, tmp_path: Path) -> Server:
    """A fresh server over the built repository."""
    return Server(built, tmp_path)


async def test_describe_names_the_history_and_its_newest_version(server: Server, built: BuiltRepository) -> None:
    """Where the file lives, six versions, the newest one last."""
    described = await server.run(DescribeHistoryAction(), DescribeHistoryParams(history="service"))
    assert (described.id, described.repository, described.branch, described.graph_file) == ("service", str(built.path), "main", GRAPH_FILE)
    assert (described.versions, described.newest) == (6, built.versions[-1])


async def test_history_lists_every_version_with_its_tags_and_facts(server: Server, built: BuiltRepository) -> None:
    """Oldest first; the tags where they belong; counts, and the refused one with its reason."""
    listed = (await server.run(HistoryAction(), HistoryParams(history="service"))).versions
    assert [v.sha for v in listed] == built.versions
    assert {v.sha: [t.name for t in v.tags] for v in listed if v.tags} == {built.sha["m1"]: ["v1.0"], built.sha["d1"]: ["v1.1"]}
    assert [(v.nodes, v.edges) for v in listed] == [(38, 28), (38, 26), (38, 25), (38, 24), (None, None), (38, 28)]
    assert listed[4].refused is not None and listed[4].refused.startswith("graph 1.1 at nodes/0")
    assert listed[1].message == "Merge pull request #1 from feature-a\n\nTwo edges fewer"


async def test_after_returns_only_later_versions(server: Server, built: BuiltRepository) -> None:
    """``after`` the third version: the last three; after the newest: none; after a commit that is not a version: not found."""
    after = await server.run(HistoryAction(), HistoryParams(history="service", after=built.sha["d1"]))
    assert [v.sha for v in after.versions] == built.versions[3:]
    newest = await server.run(HistoryAction(), HistoryParams(history="service", after=built.versions[-1]))
    assert newest.versions == []
    with pytest.raises(HistoryNotFoundError):
        await server.run(HistoryAction(), HistoryParams(history="service", after=built.sha["a1"]))


async def test_version_is_the_file_as_committed(server: Server, built: BuiltRepository) -> None:
    """A version's text is its committed bytes; a commit that is not a version, and an unknown history, are not found."""
    version = await server.run(VersionAction(), VersionParams(history="service", sha=built.sha["m1"]))
    assert version.graph == graph(edges=26)
    for params in (VersionParams(history="service", sha=built.sha["a1"]), VersionParams(history="other", sha=built.sha["m1"])):
        with pytest.raises(HistoryNotFoundError, match=r"^not found$"):
            await server.run(VersionAction(), params)


async def test_a_second_version_read_touches_neither_git_nor_the_file(server: Server, built: BuiltRepository) -> None:
    """The first read goes to git; the second, and a second read of another version of the same file, come from the cache."""
    await server.run(VersionAction(), VersionParams(history="service", sha=built.sha["d1"]))
    first = server.mirror.calls.copy()
    assert first["file_at"] == 1
    again = await server.run(VersionAction(), VersionParams(history="service", sha=built.sha["d1"]))
    assert again.graph == graph(edges=25)
    assert server.mirror.calls == first
    other = await server.run(VersionAction(), VersionParams(history="service", sha=built.sha["m3"]))
    assert other.graph == graph(edges=24)
    assert server.mirror.calls["file_at"] == 2


async def test_history_reads_each_file_once(server: Server) -> None:
    """Two listings read every version's file once in all."""
    await server.run(HistoryAction(), HistoryParams(history="service"))
    await server.run(HistoryAction(), HistoryParams(history="service"))
    assert server.mirror.calls["file_at"] == 6


async def test_the_fallback_fetch_waits_for_its_interval(server: Server) -> None:
    """With the default interval, only the first read fetches; once the interval has passed, every read does."""
    for _ in range(3):
        await server.run(HistoryAction(), HistoryParams(history="service"))
    assert server.mirror.calls["fetch"] == 1
    await server.run(HistoryAction(), HistoryParams(history="service"), AlwaysFetch)
    await server.run(DescribeHistoryAction(), DescribeHistoryParams(history="service"), AlwaysFetch)
    assert server.mirror.calls["fetch"] == 3
    assert server.mirror.calls["open"] == 1


def test_a_config_out_of_shape_is_refused(tmp_path: Path) -> None:
    """A missing field, an unknown host, an id given twice, a file that is not TOML: each refused, naming why."""
    cases = {
        '[[history]]\nid = "a"\nhost = "local"\n': "lacks repository, branch, graph_file",
        '[[history]]\nid = "a"\nhost = "gitlab"\nrepository = "r"\nbranch = "b"\ngraph_file = "g"\n': "has host 'gitlab'",
        '[[history]]\nid = "a"\nhost = "local"\nrepository = "r"\nbranch = "b"\ngraph_file = "g"\n' * 2: "is given twice",
        "[[history": "not TOML",
    }
    for text, reason in cases.items():
        config = tmp_path / "histories.toml"
        config.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError, match=reason):
            HistoriesConfig(config)
