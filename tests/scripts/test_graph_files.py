# tests/scripts/test_graph_files.py
"""The repository's saved graph (``graph-builder.toml``): the demo's, with nothing of Maxitor in it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from maxitor.graph_builder.config import read_config

from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA

REPO_ROOT = Path(__file__).resolve().parents[2]

# The graph is built in a process of its own; one that imported Maxitor, which is installed here from PyPI,
# would carry its nodes. The demo's own nodes start with its package; Maxitor's must not appear.
OWN = {"demo": "aoa.demo."}
FOREIGN = {"demo": "maxitor."}


@pytest.mark.parametrize("name", sorted(FOREIGN))
def test_a_saved_graph_holds_only_its_own_service(name: str) -> None:
    """The file is a graph of the version AOA writes, and no node in it comes from the other service."""
    (graph,) = [g for g in read_config(REPO_ROOT / "graph-builder.toml") if g.name == name]
    document = json.loads(graph.file.read_text(encoding="utf-8"))
    # AOA's own copy of the protocol's schema, the version it writes; graph-builder checks the file in a step of its own.
    Draft202012Validator(GRAPH_JSON_SCHEMA).validate(document)
    foreign = [node["id"] for node in document["nodes"] if node["id"].startswith(FOREIGN[name])]
    assert foreign == [], f"{name}: {len(foreign)} node(s) of another service, e.g. {foreign[:3]}"
    assert any(node["id"].startswith(OWN[name]) for node in document["nodes"])
