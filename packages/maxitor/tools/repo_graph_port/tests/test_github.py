# packages/maxitor/tools/repo_graph_port/tests/test_github.py
"""GitHub: a private repository through the App, pull requests and releases, webhooks routed to the histories they change."""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.server import create_app

from tests.repo_builder import GRAPH_FILE, BuiltRepository, build_repository, graph
from tests.stand_in_github import APP_ID, TOKEN, StandInGitHub, app_key
from tests.test_keys import config_file, issue

SECRET = "webhook-secret-for-tests"
BASE = "/api/v1/history"


@pytest.fixture
def world(tmp_path: Path, github_in: Path, capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    """A private GitHub repository (two graph files), the App installed, the port configured with a key to each history."""
    built = build_repository(github_in / "owner" / "service.git")
    (built.path / "billing.json").write_text(graph(edges=10), encoding="utf-8")
    subprocess.run(["git", "-C", str(built.path), "add", "billing.json"], check=True)
    subprocess.run(["git", "-C", str(built.path), "-c", "user.name=T", "-c", "user.email=t@e", "commit", "-q", "-m", "Two graph files"], check=True)
    pem, public = app_key()
    hub = StandInGitHub(public)
    config = tmp_path / "histories.toml"
    config.write_text(
        f'[github]\napp_id = {APP_ID}\nprivate_key_env = "APP_KEY"\nwebhook_secret_env = "HOOK_SECRET"\n'
        + "".join(
            f'\n[[history]]\nid = "{name}"\nhost = "github"\nrepository = "owner/service"\nbranch = "main"\ngraph_file = "{file}"\n'
            for name, file in (("orders", GRAPH_FILE), ("billing", "billing.json"))
        ),
        encoding="utf-8",
    )
    keys = {name: issue(config, capsys, name, "anna") for name in ("orders", "billing")}
    host = GitHubHost(APP_ID, pem, SECRET, transport=hub.transport())
    client = TestClient(create_app(config, tmp_path / "cache", host))
    return {"built": built, "hub": hub, "host": host, "client": client, "keys": keys, "cache": tmp_path / "cache"}


def versions(world: dict[str, Any], history: str) -> list[dict[str, Any]]:
    """The versions of ``history``, read with its key."""
    answer = world["client"].get(f"{BASE}/{history}/versions", headers={"X-Maxitor-History-Key": world["keys"][history]})
    assert answer.status_code == 200, answer.text
    return list(answer.json()["versions"])


def send(world: dict[str, Any], event: dict[str, Any], secret: str = SECRET) -> Any:
    """POST a webhook signed with ``secret``."""
    body = json.dumps(event).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return world["client"].post(f"{BASE}/events/github", content=body, headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"})


def head(world: dict[str, Any]) -> str:
    """The commit at the top of the repository's ``main``."""
    return subprocess.run(["git", "-C", str(world["built"].path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def commit(world: dict[str, Any], name: str, text: str) -> str:
    """Commit ``text`` as ``name`` on ``main``; return the commit."""
    (world["built"].path / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(world["built"].path), "add", name], check=True)
    subprocess.run(["git", "-C", str(world["built"].path), "-c", "user.name=T", "-c", "user.email=t@e", "commit", "-q", "-m", f"Change {name}"], check=True)
    return head(world)


def test_versions_carry_their_pull_request_and_their_tags_release(world: dict[str, Any]) -> None:
    """A merged pull request names its version; a version with none keeps its message; a tag carries its release."""
    built: BuiltRepository = world["built"]
    world["hub"].pulls[built.sha["m1"]] = [
        {"number": 1, "title": "Two edges fewer", "body": "Why", "html_url": "https://github.com/owner/service/pull/1", "merge_commit_sha": built.sha["m1"], "user": {"login": "anna", "avatar_url": "https://a/anna.png"}}
    ]
    world["hub"].releases["v1.0"] = {"name": "Release 1.0", "html_url": "https://github.com/owner/service/releases/tag/v1.0"}
    listed = {v["sha"]: v for v in versions(world, "orders")}
    merged, direct = listed[built.sha["m1"]], listed[built.sha["d1"]]
    assert merged["pr"] == {"number": 1, "title": "Two edges fewer", "body": "Why", "url": "https://github.com/owner/service/pull/1", "author": "anna", "avatar": "https://a/anna.png"}
    assert merged["message"] is None
    assert merged["tags"] == [{"name": "v1.0", "release": {"title": "Release 1.0", "url": "https://github.com/owner/service/releases/tag/v1.0"}}]
    assert direct["pr"] is None and direct["message"] == "Drop an edge on main"
    assert direct["tags"] == [{"name": "v1.1", "release": None}]


def test_a_push_changes_only_the_history_whose_file_it_changed(world: dict[str, Any]) -> None:
    """Two graph files in one repository: a push that changes ``billing.json`` gives ``billing`` a version and ``orders`` (``graph.json``) none."""
    before_orders, before_billing = len(versions(world, "orders")), len(versions(world, "billing"))
    before = head(world)
    after = commit(world, "billing.json", graph(edges=9))
    answer = send(world, {"ref": "refs/heads/main", "before": before, "after": after, "repository": {"full_name": "owner/service"}, "commits": []})
    assert answer.status_code == 200 and answer.json() == {"changed": ["billing"]}
    assert len(versions(world, "billing")) == before_billing + 1
    assert len(versions(world, "orders")) == before_orders


def test_a_push_that_touches_no_graph_changes_nothing(world: dict[str, Any]) -> None:
    """A README push: no history changed, and the webhook reads no graph file."""
    versions(world, "orders")
    before = head(world)
    after = commit(world, "README.md", "more words\n")
    assert send(world, {"ref": "refs/heads/main", "before": before, "after": after, "repository": {"full_name": "owner/service"}}).json() == {"changed": []}


def test_a_new_version_shows_without_waiting_for_the_interval(world: dict[str, Any]) -> None:
    """After a push's webhook, the next ``history`` has the new version, though the fallback interval has not passed."""
    first = versions(world, "orders")
    before = head(world)
    newest = commit(world, GRAPH_FILE, graph(edges=5))
    send(world, {"ref": "refs/heads/main", "before": before, "after": newest, "repository": {"full_name": "owner/service"}})
    assert [v["sha"] for v in versions(world, "orders")] == [*[v["sha"] for v in first], newest]


def test_a_pull_request_refreshes_only_a_version(world: dict[str, Any]) -> None:
    """An edited pull request whose merge commit is a version refreshes it; one whose commit is not changes nothing."""
    built: BuiltRepository = world["built"]
    versions(world, "orders")
    world["hub"].pulls[built.sha["m1"]] = [{"number": 1, "title": "Edited title", "body": "", "html_url": "u", "merge_commit_sha": built.sha["m1"]}]
    edited = {"action": "edited", "pull_request": {"merge_commit_sha": built.sha["m1"]}, "repository": {"full_name": "owner/service"}}
    assert send(world, edited).json() == {"changed": ["orders"]}
    assert {v["sha"]: v for v in versions(world, "orders")}[built.sha["m1"]]["pr"]["title"] == "Edited title"
    elsewhere = {"action": "edited", "pull_request": {"merge_commit_sha": built.sha["a1"]}, "repository": {"full_name": "owner/service"}}
    assert send(world, elsewhere).json() == {"changed": []}


def test_a_bad_signature_is_refused_and_does_nothing(world: dict[str, Any]) -> None:
    """A body signed with another secret: ``401``, the action never runs, the mirror is not fetched."""
    asked = len(world["hub"].asked)
    answer = send(world, {"ref": "refs/heads/main", "before": "0" * 40, "after": head(world), "repository": {"full_name": "owner/service"}}, secret="wrong")
    assert (answer.status_code, answer.json()) == (401, {"detail": "bad signature"})
    assert len(world["hub"].asked) == asked


def test_the_token_is_nowhere_on_disk_or_in_an_answer(world: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    """After reads that used the App's token: no file under the cache holds it — the mirror's ``config`` included — nor any output or refusal."""
    versions(world, "orders")
    refused = world["client"].get(f"{BASE}/orders/versions", headers={"X-Maxitor-History-Key": "wrong"})
    out = capsys.readouterr()
    mirror_config = world["cache"] / "mirrors" / "owner__service.git" / "config"
    assert mirror_config.is_file()
    for file in world["cache"].rglob("*"):
        if file.is_file():
            assert TOKEN.encode() not in file.read_bytes(), file
    assert TOKEN not in out.out + out.err + refused.text
    assert "extraheader" not in mirror_config.read_text(encoding="utf-8")


def test_without_an_app_a_private_history_is_not_found(tmp_path: Path, github_in: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """No ``[github]`` table: the port cannot read a private repository, and says "not found"."""
    build_repository(github_in / "owner" / "service.git")
    config = tmp_path / "histories.toml"
    config.write_text('[[history]]\nid = "orders"\nhost = "github"\nrepository = "owner/service"\nbranch = "main"\ngraph_file = "graph.json"\n', encoding="utf-8")
    key = issue(config, capsys, "orders", "anna")
    client = TestClient(create_app(config, tmp_path / "cache"))
    answer = client.get(f"{BASE}/orders/versions", headers={"X-Maxitor-History-Key": key})
    assert (answer.status_code, answer.json()) == (404, {"detail": "not found"})


def test_a_public_link_reads_the_api_with_the_apps_token(tmp_path: Path, github_in: Path) -> None:
    """With an App set, a public history's pull requests are asked with an installation's token — not anonymously, within 60 an hour."""
    public = build_repository(github_in / "other" / "open.git")
    pem, key = app_key()
    hub = StandInGitHub(key)
    hub.pulls[public.sha["m1"]] = [{"number": 9, "title": "Public PR", "body": "", "html_url": "u", "merge_commit_sha": public.sha["m1"]}]
    config = tmp_path / "histories.toml"
    config.write_text(f'[github]\napp_id = {APP_ID}\nprivate_key_env = "APP_KEY"\nwebhook_secret_env = "HOOK_SECRET"\n', encoding="utf-8")
    client = TestClient(create_app(config, tmp_path / "cache", GitHubHost(APP_ID, pem, SECRET, transport=hub.transport())))
    listed = client.get(f"{BASE}/public/versions", params={"link": "https://github.com/other/open/blob/main/graph.json"}).json()["versions"]
    assert {v["sha"]: v for v in listed}[public.sha["m1"]]["pr"]["title"] == "Public PR"
    assert hub.authorized[f"/repos/other/open/commits/{public.sha['m1']}/pulls"] == f"Bearer {TOKEN}"


def test_without_an_app_a_public_link_reads_the_api_anonymously(tmp_path: Path, github_in: Path) -> None:
    """With no App, the same reads carry no token at all."""
    public = build_repository(github_in / "other" / "open.git")
    hub = StandInGitHub(None)
    client = TestClient(create_app(config_file(tmp_path), tmp_path / "cache", GitHubHost(transport=hub.transport())))
    client.get(f"{BASE}/public/versions", params={"link": "https://github.com/other/open/blob/main/graph.json"})
    assert hub.authorized[f"/repos/other/open/commits/{public.sha['m1']}/pulls"] == ""


async def test_open_pull_requests_carry_their_review_state_and_drafts_are_left_out(world: dict[str, Any]) -> None:
    """Each reviewer's last word counts: one asking for changes outweighs an approval; none yet is "open"; a draft is no proposal."""
    hub = world["hub"]
    head = {"sha": "a" * 40}
    hub.open_pulls = [
        {"number": 7, "title": "Seven", "body": "", "html_url": "https://github.com/owner/service/pull/7", "draft": False, "head": head, "user": {"login": "olga"}},
        {"number": 8, "title": "Eight", "body": "", "html_url": "u8", "draft": False, "head": head, "user": {}},
        {"number": 9, "title": "Nine", "body": "", "html_url": "u9", "draft": False, "head": head, "user": {}},
        {"number": 10, "title": "Draft", "body": "", "html_url": "u10", "draft": True, "head": head, "user": {}},
    ]
    hub.reviews = {
        7: [{"user": {"login": "a"}, "state": "APPROVED"}, {"user": {"login": "b"}, "state": "CHANGES_REQUESTED"}],
        8: [{"user": {"login": "a"}, "state": "CHANGES_REQUESTED"}, {"user": {"login": "a"}, "state": "APPROVED"}],
    }
    pulls = await world["host"].open_pull_requests("owner/service", "main", None)
    assert [(p["number"], p["state"]) for p in pulls] == [(7, "changes_requested"), (8, "approved"), (9, "open")]
    assert pulls[0]["author"] == "olga" and pulls[0]["head"] == "a" * 40
