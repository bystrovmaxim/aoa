# packages/maxitor/tools/gnomon/tests/test_cli.py
"""The ``gnomon`` command: its lines, its fixing command and its exit codes."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from maxitor.gnomon.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, build: str = "cat printed.json") -> None:
    """A repository with one graph, ``tiny``, and the current folder at its root."""
    (tmp_path / "printed.json").write_bytes((FIXTURES / "graph-1.1.json").read_bytes())
    (tmp_path / "gnomon.toml").write_text(
        f'gnomon = "1.0"\n\n[[graph]]\nname = "tiny"\nbuild = "{build}"\nfile = "graph.json"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)


def test_write_then_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Write, write again, check: three successes, each one line."""
    _repo(tmp_path, monkeypatch)
    assert (main(["write"]), main(["write"]), main(["check"])) == (0, 0, 0)
    assert capsys.readouterr().out == "ok tiny (written)\nok tiny (unchanged)\nok tiny\n"


def test_a_stale_file_fails_the_check_with_the_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The check names the file, the difference and the command that brings it up to date."""
    _repo(tmp_path, monkeypatch)
    main(["write"])
    document = json.loads((tmp_path / "printed.json").read_text(encoding="utf-8"))
    document["nodes"].pop()
    removed = json.loads((tmp_path / "graph.json").read_text(encoding="utf-8"))["nodes"][-1]["id"]
    (tmp_path / "printed.json").write_text(json.dumps(document), encoding="utf-8")
    capsys.readouterr()
    assert main(["check"]) == 1
    assert capsys.readouterr().out.splitlines() == [
        "stale tiny: graph.json",
        f"  nodes[id={removed}]: removed",
        "run: gnomon write --config gnomon.toml, and commit the graph files",
    ]


def test_a_missing_file_fails_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Before the first write, the file is missing."""
    _repo(tmp_path, monkeypatch)
    assert main(["check"]) == 1
    assert capsys.readouterr().out.splitlines()[0] == "missing tiny: graph.json"


def test_a_failed_build_fails_with_its_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A build that gives no graph fails ``write``, and the fix names the build first."""
    _repo(tmp_path, monkeypatch, build="exit 3")
    assert main(["write"]) == 1
    assert capsys.readouterr().out.splitlines() == [
        "failed tiny",
        "  exited with 3",
        "  $ exit 3",
        "fix the build of tiny, then run: gnomon write --config gnomon.toml",
    ]


def test_a_refused_config_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No graph is built when the config is wrong; the refusal goes to standard error."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "gnomon.toml").write_text(
        'gnomon = "1.0"\n[[graph]]\nname = "tiny"\nfile = "graph.json"\n', encoding="utf-8"
    )
    assert (main(["write"]), main(["check"])) == (2, 2)
    assert capsys.readouterr().err.splitlines()[0] == "config refused: gnomon.toml: graph 'tiny', build: required"
    assert not (tmp_path / "graph.json").exists()


def test_validate_a_file(capsys: pytest.CaptureFixture[str]) -> None:
    """A graph file: its version and size."""
    assert main(["validate", str(FIXTURES / "graph-1.0.json")]) == 0
    assert capsys.readouterr().out == "ok 1.0: 38 nodes, 28 edges\n"


def test_validate_standard_input(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """``-`` reads the document from standard input, so a build can be piped in."""
    monkeypatch.setattr("sys.stdin", io.StringIO('{"schema_version": "9.9", "nodes": [], "edges": []}'))
    assert main(["validate", "-"]) == 1
    assert capsys.readouterr().out == "refused: graph 9.9: unknown schema version '9.9'; known: 1.0, 1.1\n"


def test_validate_refuses_what_is_not_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Text that is not JSON is refused as such."""
    monkeypatch.setattr("sys.stdin", io.StringIO("oops"))
    assert main(["validate", "-"]) == 1
    assert capsys.readouterr().out.startswith("refused: not JSON")


def test_skill_prints_the_setup_skill(capsys: pytest.CaptureFixture[str]) -> None:
    """``gnomon skill`` prints a skill file an agent can save as it is."""
    assert main(["skill"]) == 0
    text = capsys.readouterr().out
    assert text.startswith("---\nname: gnomon-setup\ndescription: ")
    assert "## Setup" in text and "## If you read this from a link" in text
    assert "uvx --from maxitor gnomon" in text and "maxitor-gnomon" not in text
