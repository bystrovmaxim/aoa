# packages/maxitor-gnomon/tests/test_config.py
"""``gnomon.toml``: a valid config gives its graphs in order, and every refusal names the graph and the field."""

from __future__ import annotations

from pathlib import Path

import pytest
from maxitor_gnomon.config import ConfigRefused, Graph, read_config

DEMO = """
[[graph]]
name = "demo"
cwd = "packages/aoa-demo"
build = "uv run python -m aoa.demo.build_graph"
file = "packages/aoa-demo/graph.json"
"""

MAXITOR = """
[[graph]]
name = "maxitor"
build = "uv run python -m aoa.maxitor.build_graph"
file = "packages/aoa-maxitor/graph.json"
"""


def _config(tmp_path: Path, text: str, header: str = 'gnomon = "1.0"\n') -> Path:
    """Write a config into a folder of its own and return its path."""
    path = tmp_path / "repo" / "gnomon.toml"
    path.parent.mkdir()
    path.write_text(header + text, encoding="utf-8")
    return path


def test_a_valid_config_gives_its_graphs_in_order(tmp_path: Path) -> None:
    """Graphs come in file order, ``cwd`` defaults to the config's folder, and paths are resolved against it."""
    path = _config(tmp_path, MAXITOR + DEMO)
    repo = path.parent.resolve()
    assert read_config(path) == [
        Graph("maxitor", repo, "uv run python -m aoa.maxitor.build_graph", repo / "packages/aoa-maxitor/graph.json"),
        Graph(
            "demo",
            repo / "packages/aoa-demo",
            "uv run python -m aoa.demo.build_graph",
            repo / "packages/aoa-demo/graph.json",
        ),
    ]


def test_paths_are_relative_to_the_config_not_to_the_caller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Read from another folder, the paths still start at the config's folder."""
    path = _config(tmp_path, DEMO)
    monkeypatch.chdir(tmp_path)
    (graph,) = read_config(Path("repo") / "gnomon.toml")
    assert graph.cwd == (tmp_path / "repo" / "packages/aoa-demo").resolve()
    assert graph.file == path.parent.resolve() / "packages/aoa-demo/graph.json"


@pytest.mark.parametrize(
    ("text", "graph", "field", "reason"),
    [
        (DEMO.replace('name = "demo"\n', ""), "#1", "name", "required"),
        (DEMO.replace('build = "uv run python -m aoa.demo.build_graph"\n', ""), "demo", "build", "required"),
        (DEMO.replace('file = "packages/aoa-demo/graph.json"\n', ""), "demo", "file", "required"),
        (DEMO.replace("build =", "bild ="), "demo", "bild", "not a field of the config"),
        (DEMO.replace('name = "demo"', "name = 5"), "#1", "name", "5 is not of type 'string'"),
        (
            DEMO + DEMO.replace('file = "packages/aoa-demo/graph.json"', 'file = "other.json"'),
            "demo",
            "name",
            "another graph has this name",
        ),
        (
            DEMO + MAXITOR.replace("aoa-maxitor/graph.json", "aoa-demo/graph.json"),
            "maxitor",
            "file",
            "graph 'demo' is saved in this file too",
        ),
    ],
    ids=["no-name", "no-build", "no-file", "unknown-field", "name-not-text", "repeated-name", "one-file-twice"],
)
def test_a_wrong_graph_is_refused_by_graph_and_field(
    tmp_path: Path, text: str, graph: str, field: str, reason: str
) -> None:
    """Each refusal says which graph, which field, and why."""
    with pytest.raises(ConfigRefused) as refused:
        read_config(_config(tmp_path, text))
    assert (refused.value.graph, refused.value.field, refused.value.reason) == (graph, field, reason)


def test_two_paths_to_one_file_are_one_file(tmp_path: Path) -> None:
    """``./a/../graph.json`` and ``graph.json`` are the same file."""
    text = MAXITOR.replace("packages/aoa-maxitor/graph.json", "graph.json") + DEMO.replace(
        "packages/aoa-demo/graph.json", "./packages/../graph.json"
    )
    with pytest.raises(ConfigRefused, match="graph 'maxitor' is saved in this file too"):
        read_config(_config(tmp_path, text))


@pytest.mark.parametrize(
    ("header", "text", "field", "reason"),
    [
        ("", DEMO, "gnomon", "required"),
        ('gnomon = "2.0"\n', DEMO, "gnomon", "unknown config version '2.0'; known: 1.0"),
        ('gnomon = "1.0"\n', "", "graph", "required"),
        ('gnomon = "1.0"\n', "graph = []\n", "graph", "[] should be non-empty"),
        ('gnomon = "1.0"\n', "[[graph]\n", "", "not TOML"),
    ],
    ids=["no-version", "unknown-version", "no-graphs", "empty-graphs", "not-toml"],
)
def test_a_wrong_config_is_refused_by_field(tmp_path: Path, header: str, text: str, field: str, reason: str) -> None:
    """Refusals of the config itself name no graph."""
    with pytest.raises(ConfigRefused) as refused:
        read_config(_config(tmp_path, text, header))
    assert (refused.value.graph, refused.value.field) == (None, field)
    assert refused.value.reason.startswith(reason)


def test_a_missing_config_is_refused(tmp_path: Path) -> None:
    """No file, no graphs: the refusal says where it looked."""
    with pytest.raises(ConfigRefused, match="no config at"):
        read_config(tmp_path / "gnomon.toml")


def test_a_refusal_reads_as_one_line(tmp_path: Path) -> None:
    """What a person sees: the graph, the field, the reason."""
    with pytest.raises(ConfigRefused) as refused:
        read_config(_config(tmp_path, DEMO.replace('file = "packages/aoa-demo/graph.json"\n', "")))
    assert str(refused.value) == "graph 'demo', file: required"
