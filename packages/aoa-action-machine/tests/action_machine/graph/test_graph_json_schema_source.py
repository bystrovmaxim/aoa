# packages/aoa-action-machine/tests/action_machine/graph/test_graph_json_schema_source.py
"""AOA writes graphs of version 1.1 and takes that schema from the graph format's own package."""

from __future__ import annotations

import json

from maxitor_gnomon.schemas import check_graph, graph_schema

from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA


def test_graph_json_schema_is_gnomon_1_1() -> None:
    """``GRAPH_JSON_SCHEMA`` is version 1.1 of ``maxitor-gnomon``, not a copy of it."""
    assert GRAPH_JSON_SCHEMA is graph_schema("1.1")
    assert GRAPH_JSON_SCHEMA["properties"]["schema_version"] == {"const": "1.1"}


def test_an_empty_export_is_a_gnomon_graph() -> None:
    """What AOA exports is a graph by the format's own check."""
    check_graph(json.loads('{"schema_version": "1.1", "nodes": [], "edges": []}'))
