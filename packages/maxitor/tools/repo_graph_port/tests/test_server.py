# packages/maxitor/tools/repo_graph_port/tests/test_server.py
"""The port's own server: the routes, the one "not found", the limit, the version file, a public link, a log without keys."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from maxitor.repo_graph_port.cli import main as cli
from maxitor.repo_graph_port.server import create_app

from tests.repo_builder import BuiltRepository, build_repository, graph
from tests.test_keys import config_file, issue

BASE = "/api/v1/history"


@pytest.fixture
def built(tmp_path: Path) -> BuiltRepository:
    """The shaped repository."""
    return build_repository(tmp_path / "service")


@pytest.fixture
def port(tmp_path: Path, built: BuiltRepository, capsys: pytest.CaptureFixture[str]) -> tuple[TestClient, str, Path]:
    """The port over two histories of the built repository, a key to ``orders`` for anna; the client, the key, the config."""
    path = config_file(tmp_path, str(built.path))
    key = issue(path, capsys, "orders", "anna")
    return TestClient(create_app(path, tmp_path / "cache")), key, path


def test_a_key_reads_its_history_and_the_version_file(port: tuple[TestClient, str, Path], built: BuiltRepository) -> None:
    """With anna's key: the description, the versions, a version as its committed bytes, cacheable for good."""
    client, key, _ = port
    headers = {"X-Maxitor-History-Key": key}
    described = client.get(f"{BASE}/orders", headers=headers)
    assert described.status_code == 200 and described.json()["versions"] == 6
    versions = client.get(f"{BASE}/orders/versions", headers=headers).json()["versions"]
    assert [v["sha"] for v in versions] == built.versions
    version = client.get(f"{BASE}/orders/versions/{built.sha['m1']}", headers=headers)
    assert version.status_code == 200
    assert version.content == graph(edges=26).encode("utf-8")
    assert version.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert version.headers["content-type"] == "application/json"


def test_an_unchanged_history_is_not_modified(port: tuple[TestClient, str, Path]) -> None:
    """A repeated ``history`` naming its ``ETag`` is ``304``, no body."""
    client, key, _ = port
    first = client.get(f"{BASE}/orders/versions", headers={"X-Maxitor-History-Key": key})
    again = client.get(f"{BASE}/orders/versions", headers={"X-Maxitor-History-Key": key, "If-None-Match": first.headers["etag"]})
    assert again.status_code == 304 and again.content == b""


def test_every_refusal_is_the_same_not_found(port: tuple[TestClient, str, Path], built: BuiltRepository, capsys: pytest.CaptureFixture[str]) -> None:
    """No key, a wrong key, anna's key on ``billing``, an expired key, an unknown history, a commit that is not a version."""
    client, key, path = port
    expired = issue(path, capsys, "orders", "old", "--expires", "2020-01-01")
    asks = [
        (f"{BASE}/orders/versions", None),
        (f"{BASE}/orders/versions", "x" * 43),
        (f"{BASE}/billing/versions", key),
        (f"{BASE}/orders/versions", expired),
        (f"{BASE}/nope/versions", key),
        (f"{BASE}/orders/versions/{built.sha['a1']}", key),
    ]
    for url, held in asks:
        answer = client.get(url, headers={"X-Maxitor-History-Key": held} if held else {})
        assert (answer.status_code, answer.json()) == (404, {"detail": "not found"}), url


def test_too_many_wrong_keys_are_refused(port: tuple[TestClient, str, Path]) -> None:
    """The eleventh wrong key from one client within a minute: ``429``."""
    client, _, _ = port
    codes = [client.get(f"{BASE}/orders", headers={"X-Maxitor-History-Key": "wrong"}).status_code for _ in range(11)]
    assert codes == [404] * 10 + [429]


def test_a_public_link_opens_with_no_key(tmp_path: Path, github_in: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A link to a public repository's graph file opens its history and a version, with no key and no config entry."""
    public = build_repository(github_in / "owner" / "service.git")
    client = TestClient(create_app(config_file(tmp_path), tmp_path / "cache"))
    link = "https://github.com/owner/service/blob/main/graph.json"
    versions = client.get(f"{BASE}/public/versions", params={"link": link}).json()["versions"]
    assert [v["sha"] for v in versions] == public.versions
    version = client.get(f"{BASE}/public/versions/{public.sha['d1']}", params={"link": link})
    assert version.content == graph(edges=25).encode("utf-8")
    nowhere = client.get(f"{BASE}/public/versions", params={"link": "https://github.com/owner/missing/blob/main/graph.json"})
    assert (nowhere.status_code, nowhere.json()) == (404, {"detail": "not found"})
    assert client.get(f"{BASE}/public/versions", params={"link": "https://example.com/graph.json"}).status_code == 404


def test_the_log_names_the_reader_never_the_key(port: tuple[TestClient, str, Path], built: BuiltRepository, capsys: pytest.CaptureFixture[str]) -> None:
    """After reads with the key and refusals, the captured output names anna and ``orders``; neither the key nor its hash."""
    client, key, _ = port
    capsys.readouterr()
    client.get(f"{BASE}/orders/versions", headers={"X-Maxitor-History-Key": key})
    client.get(f"{BASE}/orders/versions/{built.sha['m1']}", headers={"X-Maxitor-History-Key": key})
    refused = client.get(f"{BASE}/billing/versions", headers={"X-Maxitor-History-Key": key})
    out = capsys.readouterr()
    said = out.out + out.err + refused.text
    assert "anna" in said and "orders" in said
    assert key not in said and hashlib.sha256(key.encode()).hexdigest() not in said


def test_the_server_refuses_a_config_out_of_shape(tmp_path: Path) -> None:
    """A broken config stops the server before it exists."""
    broken = tmp_path / "histories.toml"
    broken.write_text('[[history]]\nid = "public"\nhost = "local"\nrepository = "r"\nbranch = "b"\ngraph_file = "g"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="reserved"):
        create_app(broken, tmp_path / "cache")
    assert cli(["--config", str(broken), "check"]) == 2
