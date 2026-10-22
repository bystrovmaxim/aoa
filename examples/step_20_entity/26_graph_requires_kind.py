"""Reject graph data without entity_kind.

An older Entity row that only contains a description no longer satisfies the interchange schema.

Run: uv run python examples/step_20_entity/26_graph_requires_kind.py
"""

from jsonschema import Draft202012Validator, ValidationError

from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA

payload = {
    "schema_version": "1.0",
    "nodes": [{"id": "shop.OrderCoreEntity", "type": "Entity", "label": "OrderCoreEntity",
               "properties": {"description": "Customer order"}}],
    "edges": [],
}
try:
    Draft202012Validator(GRAPH_JSON_SCHEMA).validate(payload)
except ValidationError:
    print("Entity row without entity_kind: rejected")
else:
    raise AssertionError("An Entity row must carry its kind")
