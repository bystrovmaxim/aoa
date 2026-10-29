# packages/maxitor/tools/repo_graph_port/tests/test_keys.py
"""Read keys: the config keeps only hashes, a key opens one history, expiry and revocation, the key commands."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from maxitor.repo_graph_port.auth.history_key_auth_coordinator import HistoryKeyAuthCoordinator
from maxitor.repo_graph_port.cli import main as cli
from maxitor.repo_graph_port.history_reader_info import HistoryReaderInfo
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.too_many_wrong_keys_error import TooManyWrongKeysError

TWO_HISTORIES = """# two histories of one repository
[[history]]
id = "orders"
host = "local"
repository = "{repository}"
branch = "main"
graph_file = "graph.json"

[[history]]
id = "billing"
host = "local"
repository = "{repository}"
branch = "main"
graph_file = "billing/graph.json"
"""


def config_file(tmp_path: Path, repository: str = "/nowhere") -> Path:
    """A config of two histories of one repository, with no key yet."""
    path = tmp_path / "histories.toml"
    path.write_text(TWO_HISTORIES.format(repository=repository), encoding="utf-8")
    return path


def issue(path: Path, capsys: pytest.CaptureFixture[str], history: str, name: str, *more: str) -> str:
    """``key new`` for ``name`` on ``history``; the key it printed."""
    assert cli(["--config", str(path), "key", "new", "--history", history, "--name", name, *more]) == 0
    return capsys.readouterr().out.strip()


def request(key: str | None, client: str = "10.0.0.1") -> SimpleNamespace:
    """A request as the coordinator reads it: headers, path, client."""
    headers = {"x-maxitor-history-key": key} if key is not None else {}
    return SimpleNamespace(headers=headers, url=SimpleNamespace(path="/api/v1/history/orders"), method="GET", client=SimpleNamespace(host=client))


def test_key_new_prints_the_key_once_and_keeps_only_its_hash(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The file gets the name and the SHA-256; the key itself is printed and nowhere in the file; comments survive."""
    path = config_file(tmp_path)
    key = issue(path, capsys, "orders", "anna")
    text = path.read_text(encoding="utf-8")
    assert len(key) == 43 and key not in text
    assert hashlib.sha256(key.encode()).hexdigest() in text and 'name = "anna"' in text
    assert text.startswith("# two histories of one repository")


def test_a_key_opens_its_history_and_no_other(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A key to ``orders`` reads as anna on ``orders``; it is not a key to ``billing`` of the same repository."""
    path = config_file(tmp_path)
    key = issue(path, capsys, "orders", "anna")
    config = HistoriesConfig(path)
    digest = hashlib.sha256(key.encode()).hexdigest()
    assert config.reader_of(digest, date(2026, 10, 29)) == ("orders", "anna")
    assert [entry for entry in config.keys("billing")] == []


async def test_expired_revoked_and_unknown_keys_read_as_a_guest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Each wrong key gives the same reader as no key — a guest with no history — so the action's answer is the same."""
    path = config_file(tmp_path)
    expired = issue(path, capsys, "orders", "old", "--expires", "2020-01-01")
    revoked = issue(path, capsys, "orders", "gone")
    good = issue(path, capsys, "orders", "anna")
    assert cli(["--config", str(path), "key", "revoke", "--history", "orders", "--name", "gone"]) == 0
    coordinator = HistoryKeyAuthCoordinator(HistoriesConfig(path))
    readers = [(await coordinator.process(request(key))).user for key in (expired, revoked, "x" * 43, None)]
    assert all(isinstance(r, HistoryReaderInfo) and r.history == "" and r.user_id is None for r in readers)
    opened = (await coordinator.process(request(good))).user
    assert isinstance(opened, HistoryReaderInfo) and (opened.user_id, opened.history) == ("anna", "orders")


async def test_wrong_keys_from_one_client_are_limited(tmp_path: Path) -> None:
    """The eleventh wrong key from one address within a minute is refused; another address is not."""
    coordinator = HistoryKeyAuthCoordinator(HistoriesConfig(config_file(tmp_path)))
    for _ in range(10):
        await coordinator.process(request("wrong"))
    with pytest.raises(TooManyWrongKeysError):
        await coordinator.process(request("wrong"))
    await coordinator.process(request("wrong", client="10.0.0.2"))


def test_the_config_is_reread_when_it_changes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A key issued while the port runs opens at once; a revoked one stops at once."""
    path = config_file(tmp_path)
    config = HistoriesConfig(path)
    key = issue(path, capsys, "orders", "anna")
    digest = hashlib.sha256(key.encode()).hexdigest()
    assert config.reader_of(digest, date(2026, 10, 29)) == ("orders", "anna")
    cli(["--config", str(path), "key", "revoke", "--history", "orders", "--name", "anna"])
    assert config.reader_of(digest, date(2026, 10, 29)) is None


def test_key_list_shows_names_and_dates_never_keys_or_hashes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """One line per key: history, name, expiry."""
    path = config_file(tmp_path)
    key = issue(path, capsys, "orders", "anna", "--expires", "2027-06-01")
    assert cli(["--config", str(path), "key", "list"]) == 0
    listed = capsys.readouterr().out
    assert listed == "orders\tanna\t2027-06-01\n"
    assert key not in listed and hashlib.sha256(key.encode()).hexdigest() not in listed


def test_key_commands_refuse_what_they_cannot_do(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown history, a name given twice, a key not there, a broken config: exit 2, the file unchanged."""
    path = config_file(tmp_path)
    issue(path, capsys, "orders", "anna")
    before = path.read_text(encoding="utf-8")
    assert cli(["--config", str(path), "key", "new", "--history", "nope", "--name", "x"]) == 2
    assert cli(["--config", str(path), "key", "new", "--history", "orders", "--name", "anna"]) == 2
    assert cli(["--config", str(path), "key", "revoke", "--history", "orders", "--name", "nobody"]) == 2
    assert path.read_text(encoding="utf-8") == before
    broken = tmp_path / "broken.toml"
    broken.write_text("[[history", encoding="utf-8")
    assert cli(["--config", str(broken), "key", "list"]) == 2


def test_check_finds_each_graph_file_on_its_branch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A history whose file is on its branch passes; one whose file is not fails the check with exit 1."""
    from tests.repo_builder import build_repository

    built = build_repository(tmp_path / "service")
    path = config_file(tmp_path, str(built.path))
    assert cli(["--config", str(path), "check"]) == 1
    said = capsys.readouterr().out
    assert "ok  orders: ok" in said and "FAIL billing: no billing/graph.json on main" in said


def test_nothing_shows_a_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The config's, the coordinator's and the authenticator's ``repr`` name the file, never a key or its hash."""
    path = config_file(tmp_path)
    key = issue(path, capsys, "orders", "anna")
    coordinator = HistoryKeyAuthCoordinator(HistoriesConfig(path))
    shown = repr(coordinator) + repr(coordinator.authenticator) + repr(HistoriesConfig(path))
    assert str(path) in shown
    assert key not in shown and hashlib.sha256(key.encode()).hexdigest() not in shown


def test_check_says_when_a_private_history_has_no_app(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A GitHub history with no ``[github]`` App: the check fails and says why, without trying an anonymous clone."""
    path = tmp_path / "histories.toml"
    path.write_text('[[history]]\nid = "orders"\nhost = "github"\nrepository = "owner/private"\nbranch = "main"\ngraph_file = "graph.json"\n', encoding="utf-8")
    assert cli(["--config", str(path), "check"]) == 1
    assert capsys.readouterr().out == "FAIL orders: no [github] App to read a private repository with\n"
