# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/get_lifecycle_finite_automaton_action_schema.py
"""
get_lifecycle_finite_automaton_action_schema — JSON Schema for ``GetLifecycleFiniteAutomatonAction.Result``.

Wire object for one interchange ``Lifecycle`` vertex template (states + edges).
"""

from __future__ import annotations

from aoa.action_machine.model import JsonSchemaValue

_STATE_ITEM = {
    "type": "object",
    "properties": {
        "key": {"type": "string"},
        "display_name": {"type": "string"},
        "state_type": {"type": "string"},
        "transitions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["key", "display_name", "state_type", "transitions"],
    "additionalProperties": False,
}

_EDGE_ITEM = {
    "type": "object",
    "properties": {
        "source": {"type": "string"},
        "target": {"type": "string"},
    },
    "required": ["source", "target"],
    "additionalProperties": False,
}

# {
#   "lifecycle_graph_node_id": "aoa...Entity:lifecycle:status",
#   "host_entity_type_qualname": "aoa...Entity",
#   "field_name": "status",
#   "lifecycle_class_qualname": "aoa...OrderLifecycle",
#   "initial_state_keys": ["new"],
#   "states": [
#     {"key": "new", "display_name": "New", "state_type": "initial", "transitions": ["confirmed"]}
#   ],
#   "transitions": [{"source": "new", "target": "confirmed"}]
# }
LifecycleFiniteAutomatonJson = JsonSchemaValue.define(
    name="LifecycleFiniteAutomatonJson",
    schema={
        "type": "object",
        "properties": {
            "lifecycle_graph_node_id": {"type": "string"},
            "host_entity_type_qualname": {"type": "string"},
            "field_name": {"type": "string"},
            "lifecycle_class_qualname": {"type": "string"},
            "initial_state_keys": {"type": "array", "items": {"type": "string"}},
            "states": {"type": "array", "items": _STATE_ITEM},
            "transitions": {"type": "array", "items": _EDGE_ITEM},
        },
        "required": [
            "lifecycle_graph_node_id",
            "host_entity_type_qualname",
            "field_name",
            "lifecycle_class_qualname",
            "initial_state_keys",
            "states",
            "transitions",
        ],
        "additionalProperties": False,
    },
)
