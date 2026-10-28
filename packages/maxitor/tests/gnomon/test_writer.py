# packages/maxitor/tests/gnomon/test_writer.py
"""``write`` and ``check`` on tiny graphs printed by ``cat``: the same bytes, untouched files, named failures."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest
from maxitor.gnomon.config import Graph
from maxitor.gnomon.writer import check, render, write

FIXTURES = Path(__file__).parent / "fixtures"


def _source(tmp_path: Path) -> Path:
    """Where the build reads the graph it prints; tests change it to change the graph."""
    return tmp_path / "printed.json"


def _graph(tmp_path: Path, build: str | None = None) -> Graph:
    """A graph whose build prints ``printed.json``, saved in ``saved/graph.json``."""
    return Graph("tiny", tmp_path, build or f"cat {_source(tmp_path).name}", tmp_path / "saved" / "graph.json")


def _print(tmp_path: Path, document: dict[str, Any]) -> None:
    """Make the build print ``document``, written in an order and an indent of its own."""
    _source(tmp_path).write_text(json.dumps(document, indent=4), encoding="utf-8")


def _sample() -> dict[str, Any]:
    """A valid 1.1 graph."""
    document: dict[str, Any] = json.loads((FIXTURES / "graph-1.1.json").read_text(encoding="utf-8"))
    return document


def test_two_writes_give_the_same_bytes(tmp_path: Path) -> None:
    """The file is the rendered document — sorted keys, indent 2 — whatever order the build printed."""
    document = _sample()
    _print(tmp_path, document)
    graph = _graph(tmp_path)
    assert [o.state for o in write([graph])] == ["written"]
    first = graph.file.read_bytes()
    reordered = {key: document[key] for key in reversed(list(document))}
    _print(tmp_path, reordered)
    graph.file.unlink()
    write([graph])
    assert graph.file.read_bytes() == first == render(document)
    assert first.endswith(b"}\n") and first.startswith(b'{\n  "edges": [')


def test_an_unchanged_graph_leaves_the_file_untouched(tmp_path: Path) -> None:
    """A second write of the same graph neither rewrites the bytes nor moves the file's time."""
    _print(tmp_path, _sample())
    graph = _graph(tmp_path)
    write([graph])
    past = time.time() - 3600
    os.utime(graph.file, (past, past))
    assert [o.state for o in write([graph])] == ["unchanged"]
    assert graph.file.stat().st_mtime == past


def test_check_passes_right_after_a_write(tmp_path: Path) -> None:
    """What ``write`` wrote is what ``check`` expects."""
    _print(tmp_path, _sample())
    graph = _graph(tmp_path)
    write([graph])
    assert [(o.state, o.ok) for o in check([graph])] == [("current", True)]


def test_check_names_the_differences_by_id_and_writes_nothing(tmp_path: Path) -> None:
    """After the model changes, ``check`` fails, says what changed, and leaves the stale file as it was."""
    document = _sample()
    _print(tmp_path, document)
    graph = _graph(tmp_path)
    write([graph])
    stale = graph.file.read_bytes()
    edge = document["edges"][0]
    edge["is_dag"] = not edge["is_dag"]
    _print(tmp_path, document)
    (outcome,) = check([graph])
    assert (outcome.state, outcome.ok) == ("stale", False)
    assert outcome.details == (
        f"edges[id={edge['id']}].is_dag: {json.dumps(not edge['is_dag'])} → {json.dumps(edge['is_dag'])}",
    )
    assert graph.file.read_bytes() == stale


def test_only_the_formatting_differs(tmp_path: Path) -> None:
    """A re-indented file holds the same graph; ``check`` says so and still fails."""
    document = _sample()
    _print(tmp_path, document)
    graph = _graph(tmp_path)
    write([graph])
    graph.file.write_text(json.dumps(document, indent=4), encoding="utf-8")
    (outcome,) = check([graph])
    assert (outcome.state, outcome.details) == ("stale", ("only the formatting differs",))


def test_a_missing_file_is_named(tmp_path: Path) -> None:
    """No file yet: ``check`` says it is missing and does not create it."""
    _print(tmp_path, _sample())
    graph = _graph(tmp_path)
    assert [o.state for o in check([graph])] == ["missing"]
    assert not graph.file.exists()


@pytest.mark.parametrize(
    ("build", "state", "first_detail"),
    [
        ("echo partial; echo broken >&2; exit 3", "failed", "exited with 3"),
        ("echo oops", "failed", "printed something that is not JSON"),
        (
            'echo \'{"schema_version": "1.1", "nodes": [], "edges": [{"source_id": "a"}]}\'',
            "refused",
            "graph 1.1 at edges/0",
        ),
        ("sleep 5", "failed", "took longer than 1 s"),
    ],
    ids=["exit-3", "not-json", "not-a-graph", "too-slow"],
)
def test_a_build_that_gives_no_graph_writes_nothing(tmp_path: Path, build: str, state: str, first_detail: str) -> None:
    """Each failure names the graph and why; neither ``write`` nor ``check`` touches the file."""
    graph = _graph(tmp_path, build)
    started = time.monotonic()
    for outcome in (*write([graph], timeout=1), *check([graph], timeout=1)):
        assert (outcome.graph.name, outcome.state, outcome.ok) == ("tiny", state, False)
        assert outcome.details[0].startswith(first_detail)
    assert time.monotonic() - started < 4
    assert not graph.file.exists()


def test_a_failed_build_shows_its_command_and_output(tmp_path: Path) -> None:
    """The person fixing the build sees what ran and what it said."""
    (outcome,) = write([_graph(tmp_path, "echo partial; echo broken >&2; exit 3")])
    assert outcome.details == ("exited with 3", "$ echo partial; echo broken >&2; exit 3", "broken", "partial")


def test_a_timed_out_build_stops_everything_it_started(tmp_path: Path) -> None:
    """The time limit stops the build's children too, not only the shell."""
    marker = tmp_path / "late"
    write([_graph(tmp_path, f"(sleep 2; touch {marker}) & sleep 5")], timeout=0.5)
    time.sleep(2.5)
    assert not marker.exists()
