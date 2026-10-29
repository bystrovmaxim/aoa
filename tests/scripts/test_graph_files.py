# tests/scripts/test_graph_files.py
"""The repository's saved graphs (``graph-builder.toml``): each holds its own service and nothing of the other."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from maxitor.graph_builder.config import read_config
from maxitor.graph_builder.schemas import check_graph

REPO_ROOT = Path(__file__).resolve().parents[2]

# Each graph is built in a process of its own; one that imported the other's package would carry its nodes.
# Each service's own nodes start with its package; the other's must not appear.
OWN = {"demo": "aoa.demo.", "maxitor": "maxitor.front."}
FOREIGN = {"demo": OWN["maxitor"], "maxitor": OWN["demo"]}


@pytest.mark.parametrize("name", sorted(FOREIGN))
def test_a_saved_graph_holds_only_its_own_service(name: str) -> None:
    """The file is a graph, and no node in it comes from the other service."""
    (graph,) = [g for g in read_config(REPO_ROOT / "graph-builder.toml") if g.name == name]
    document = json.loads(graph.file.read_text(encoding="utf-8"))
    check_graph(document)
    foreign = [node["id"] for node in document["nodes"] if node["id"].startswith(FOREIGN[name])]
    assert foreign == [], f"{name}: {len(foreign)} node(s) of another service, e.g. {foreign[:3]}"
    assert any(node["id"].startswith(OWN[name]) for node in document["nodes"])
