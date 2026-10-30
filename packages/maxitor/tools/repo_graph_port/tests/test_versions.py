# packages/maxitor/tools/repo_graph_port/tests/test_versions.py
"""A history from git: exactly the first-parent commits that changed the graph, their tags, their files and facts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from maxitor.repo_graph_port.git_error import GitError
from maxitor.repo_graph_port.history_versions import graph_change, graph_facts, place_tags, pull_request_in_message
from maxitor.repo_graph_port.resources.git_mirror import GitMirror

from tests.repo_builder import GRAPH_FILE, BuiltRepository, add_version, build_repository, graph


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> BuiltRepository:
    """The shaped repository, built once for the module."""
    return build_repository(tmp_path_factory.mktemp("history") / "service")


def _local(built: BuiltRepository, tmp_path: Path) -> tuple[GitMirror, str]:
    """A mirror reading the built repository as a local path."""
    mirror = GitMirror(tmp_path / "cache")
    mirror.open(str(built.path))
    return mirror, str(built.path)


def test_versions_are_the_first_parent_commits_that_changed_the_file(built: BuiltRepository, tmp_path: Path) -> None:
    """Oldest first; the branch commits, the README commits and the merge that left the file alone are absent."""
    mirror, repository = _local(built, tmp_path)
    shas = [commit.sha for commit in mirror.versions(repository, "main", GRAPH_FILE)]
    for absent in ("pre", "readme", "a1", "a2", "m2", "c1"):
        assert built.sha[absent] not in shas, f"{absent} is listed as a version"
    assert shas == built.versions


def test_a_version_carries_its_date_in_utc_and_its_message(built: BuiltRepository, tmp_path: Path) -> None:
    """The committer date, written as 00:07 at +03:00 on 1 October, comes back in UTC; a merge keeps its whole message."""
    mirror, repository = _local(built, tmp_path)
    first, merged = mirror.versions(repository, "main", GRAPH_FILE)[:2]
    assert first.date == "2026-09-30T21:07:00Z"
    assert first.message == "Add the graph"
    assert merged.message == "Merge pull request #1 from feature-a\n\nTwo edges fewer"


def test_tags_land_on_the_version_they_belong_to(built: BuiltRepository, tmp_path: Path) -> None:
    """On a version's own commit; on a later commit — the version before it; off the chain or before the graph — nowhere."""
    mirror, repository = _local(built, tmp_path)
    chain = mirror.first_parents(repository, "main")
    placed = place_tags(chain, built.versions, mirror.tags(repository))
    assert placed == {built.sha["m1"]: ["v1.0"], built.sha["d1"]: ["v1.1"]}


def test_an_annotated_tag_is_followed_to_its_commit(built: BuiltRepository, tmp_path: Path) -> None:
    """``v1.0`` is an annotated tag: its ``sha`` is the merge commit, not the tag object."""
    mirror, repository = _local(built, tmp_path)
    tags = {tag.name: tag.sha for tag in mirror.tags(repository)}
    assert tags["v1.0"] == built.sha["m1"]


def test_each_version_file_comes_back_byte_for_byte(built: BuiltRepository, tmp_path: Path) -> None:
    """The bytes git stored, not a re-serialised document."""
    mirror, repository = _local(built, tmp_path)
    assert mirror.file_at(repository, built.sha["m1"], GRAPH_FILE) == graph(edges=26).encode("utf-8")
    assert mirror.file_at(repository, built.sha["pre"], GRAPH_FILE) is None


def test_facts_count_a_graph_and_name_a_refusal(built: BuiltRepository, tmp_path: Path) -> None:
    """Every version counted, the broken one refused with the protocol's reason, the ``1.0`` one counted too."""
    mirror, repository = _local(built, tmp_path)
    facts = {sha: graph_facts(mirror.file_at(repository, sha, GRAPH_FILE) or b"") for sha in built.versions}
    assert [(f.nodes, f.edges) for f in facts.values()] == [(38, 28), (38, 26), (38, 25), (38, 24), (None, None), (38, 28)]
    refused = facts[built.sha["bad"]].refused
    assert refused is not None and refused.startswith("graph 1.1 at nodes/0")
    assert graph_facts(b"{not json").refused is not None


def test_a_mirror_reads_the_same_history_and_fetches_what_is_new(tmp_path: Path) -> None:
    """A bare partial mirror of the repository's URL lists the same versions, and ``fetch`` brings a new one."""
    built = build_repository(tmp_path / "origin")
    mirror = GitMirror(tmp_path / "cache")
    mirror.open("owner/service", url=built.path.as_uri())
    assert [c.sha for c in mirror.versions("owner/service", "main", GRAPH_FILE)] == built.versions
    assert mirror.file_at("owner/service", built.sha["d1"], GRAPH_FILE) == graph(edges=25).encode("utf-8")
    newest = add_version(built, edges=20)
    mirror.fetch("owner/service")
    assert [c.sha for c in mirror.versions("owner/service", "main", GRAPH_FILE)] == [*built.versions, newest]
    assert (tmp_path / "cache" / "mirrors" / "owner__service.git").is_dir()


def test_git_failures_are_named_and_unopened_repositories_refused(built: BuiltRepository, tmp_path: Path) -> None:
    """An unknown branch is a ``GitError`` naming the subcommand; a name never opened is a ``KeyError``; a bad mirror name a ``ValueError``."""
    mirror, repository = _local(built, tmp_path)
    with pytest.raises(GitError, match=r"^git log failed: "):
        mirror.versions(repository, "no-such-branch", GRAPH_FILE)
    with pytest.raises(KeyError):
        mirror.tags("never/opened")
    with pytest.raises(ValueError):
        mirror.open("../escape", url="file:///nowhere")


def test_a_failed_clone_leaves_no_mirror_behind(tmp_path: Path) -> None:
    """A clone that fails leaves nothing in the cache, so the next open clones again instead of reading half a mirror."""
    mirror = GitMirror(tmp_path / "cache")
    with pytest.raises(GitError):
        mirror.open("owner/missing", url=(tmp_path / "nowhere").as_uri())
    assert list((tmp_path / "cache" / "mirrors").iterdir()) == []
    built = build_repository(tmp_path / "origin")
    mirror.open("owner/missing", url=built.path.as_uri())
    assert [c.sha for c in mirror.versions("owner/missing", "main", GRAPH_FILE)] == built.versions


class _TimingOutMirror(GitMirror):
    """A mirror whose clone starts writing its folder, then runs out of time — what a stalled network does."""

    def _git(self, place: Path | None, arguments: list[str], auth: Mapping[str, str] | None = None) -> bytes:
        """Make the clone's target folder, then give up the way a timeout does."""
        if arguments[0] == "clone":
            Path(arguments[-1]).mkdir(parents=True)
            raise GitError("clone", "no answer in 300 s")
        return super()._git(place, arguments, auth)


def test_a_clone_that_times_out_leaves_no_mirror_behind(tmp_path: Path) -> None:
    """A clone cut off by its timeout leaves no folder that a later open would take for a whole mirror."""
    mirror = _TimingOutMirror(tmp_path / "cache")
    with pytest.raises(GitError, match="no answer"):
        mirror.open("owner/slow", url="https://example.invalid/owner/slow.git")
    assert list((tmp_path / "cache" / "mirrors").iterdir()) == []


def test_a_merge_commit_names_its_pull_request_without_the_merge_line() -> None:
    message = "Merge pull request #147 from owner/offer-regions\n\nOffer regions: an offer is shown only in the regions it lists\n\nModel\n- regions is a list."
    assert pull_request_in_message(message, "https://github.com/owner/repo/pull/") == {
        "number": 147,
        "title": "Offer regions: an offer is shown only in the regions it lists",
        "body": "Model\n- regions is a list.",
        "url": "https://github.com/owner/repo/pull/147",
    }


def test_a_squash_commit_names_its_pull_request() -> None:
    assert pull_request_in_message("Ticket import from CSV (#142)\n\nTickets come from a CSV file.", "") == {
        "number": 142,
        "title": "Ticket import from CSV",
        "body": "Tickets come from a CSV file.",
        "url": "",
    }


def test_a_direct_commit_names_no_pull_request() -> None:
    assert pull_request_in_message("Fix a typo in #12's description", "") is None


def test_a_versions_change_counts_nodes_by_kind_nodes_changed_and_links() -> None:
    """Nodes by id — added and removed by kind, kept but different; edges by id, or by their ends when they have none."""
    before = json.dumps({"nodes": [{"id": "a", "type": "Entity"}, {"id": "b", "type": "Field", "label": "x"}, {"id": "c", "type": "Field"}],
                         "edges": [{"id": "a-b"}, {"source_id": "a", "relationship": "has", "target_id": "c"}]}).encode()
    after = json.dumps({"nodes": [{"id": "a", "type": "Entity"}, {"id": "b", "type": "Field", "label": "y"}, {"id": "d", "type": "Action"}],
                        "edges": [{"id": "a-b"}, {"id": "a-d"}, {"id": "b-d"}]}).encode()
    assert graph_change(before, after) == {"added": {"Action": 1}, "removed": {"Field": 1}, "changed": 1, "links": {"added": 2, "removed": 1}}
    assert graph_change(None, after)["added"] == {"Action": 1, "Entity": 1, "Field": 1}
    assert graph_change(b"not json", after)["links"] == {"added": 3, "removed": 0}
