# packages/maxitor/tools/repo_graph_port/tests/test_live_and_reader.py
"""``describe`` names a history's Live service and the key's holder; a public link has neither; a bad ``live`` refuses the config."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from maxitor.repo_graph_port.cli import main as cli
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.server import create_app

from tests.repo_builder import build_repository
from tests.stand_in_github import StandInGitHub
from tests.test_keys import issue

BASE = "/api/v1/history"

WITH_LIVE = """[[history]]
id = "orders"
host = "local"
repository = "{repository}"
branch = "main"
graph_file = "graph.json"
live = "https://orders.example.com"

[[history]]
id = "billing"
host = "local"
repository = "{repository}"
branch = "main"
graph_file = "billing/graph.json"
"""


def live_config(tmp_path: Path, repository: str, live: str = "https://orders.example.com") -> Path:
    """Two histories of one repository; ``orders`` names ``live``, ``billing`` names none."""
    path = tmp_path / "histories.toml"
    path.write_text(WITH_LIVE.format(repository=repository).replace("https://orders.example.com", live), encoding="utf-8")
    return path


def test_describe_gives_live_and_the_reader(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``orders`` answers its ``live`` and anna; ``billing`` answers no ``live``."""
    built = build_repository(tmp_path / "service")
    path = live_config(tmp_path, str(built.path))
    anna = issue(path, capsys, "orders", "anna")
    boris = issue(path, capsys, "billing", "boris")
    client = TestClient(create_app(path, tmp_path / "cache"))
    orders = client.get(f"{BASE}/orders", headers={"X-Maxitor-History-Key": anna}).json()
    assert (orders["live"], orders["reader"]) == ("https://orders.example.com", "anna")
    billing = client.get(f"{BASE}/billing", headers={"X-Maxitor-History-Key": boris}).json()
    assert (billing["live"], billing["reader"]) == (None, "boris")


def test_a_public_link_has_no_live_and_no_reader(tmp_path: Path, github_in: Path) -> None:
    """A public history answers neither ``live`` nor ``reader``."""
    build_repository(github_in / "owner" / "service.git")
    path = tmp_path / "histories.toml"
    path.write_text("", encoding="utf-8")
    client = TestClient(create_app(path, tmp_path / "cache", GitHubHost(transport=StandInGitHub(None).transport())))
    described = client.get(f"{BASE}/public", params={"link": "https://github.com/owner/service/blob/main/graph.json"}).json()
    assert described["versions"] == 6
    assert (described["live"], described["reader"]) == (None, None)


@pytest.mark.parametrize("live", ["orders.example.com", "ftp://orders.example.com", "https://"])
def test_a_live_that_is_not_an_http_url_refuses_the_config(tmp_path: Path, live: str, capsys: pytest.CaptureFixture[str]) -> None:
    """A ``live`` with no scheme, another scheme or no host: the server is not built and ``check`` exits 2, naming the history."""
    path = live_config(tmp_path, "/nowhere", live)
    with pytest.raises(ValueError, match="history 'orders' has live"):
        create_app(path, tmp_path / "cache")
    assert cli(["--config", str(path), "check"]) == 2
    assert "an http(s) URL is needed" in capsys.readouterr().err
