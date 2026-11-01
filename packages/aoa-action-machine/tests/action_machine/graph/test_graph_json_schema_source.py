# packages/aoa-action-machine/tests/action_machine/graph/test_graph_json_schema_source.py
"""AOA writes graphs of version 1.1 and checks them against its own copy of the protocol's schema."""

from __future__ import annotations

from jsonschema import Draft202012Validator

from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA


def test_graph_json_schema_is_protocol_1_2() -> None:
    """``GRAPH_JSON_SCHEMA`` is version 1.2 of the Open Gnomon Protocol, addressed by its raw ``$id``."""
    assert GRAPH_JSON_SCHEMA["properties"]["schema_version"] == {"const": "1.2"}
    assert GRAPH_JSON_SCHEMA["$id"].endswith("/packages/open-gnomon-protocol/graph/1.2.json")


def test_an_empty_export_is_a_graph() -> None:
    """An empty export passes the schema with a plain JSON Schema validator."""
    Draft202012Validator(GRAPH_JSON_SCHEMA).validate({"schema_version": "1.2", "nodes": [], "edges": []})
