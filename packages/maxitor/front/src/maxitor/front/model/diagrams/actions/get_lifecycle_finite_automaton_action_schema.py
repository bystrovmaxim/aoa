# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/get_lifecycle_finite_automaton_action_schema.py
"""
get_lifecycle_finite_automaton_action_schema — JSON Schema for ``GetLifecycleFiniteAutomatonAction.Result``.

Wire object for one interchange ``Lifecycle`` vertex template (states + edges).
"""

from __future__ import annotations

from aoa.action_machine.model import JsonSchemaValue

_ATTRIBUTES_ITEM = {
    "type": "object",
    "properties": {
        "code": {"type": "string"},
        "display_name": {"type": "string"},
        "sort_order": {"type": ["integer", "number"]},
        "color": {"type": "string"},
        "fill_color": {"type": "string"},
    },
    "additionalProperties": False,
}

_STATE_ITEM = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "key": {"type": "string"},
        "display_name": {"type": "string"},
        "state_type": {"type": "string"},
        "transitions": {"type": "array", "items": {"type": "string"}},
        "attributes": _ATTRIBUTES_ITEM,
    },
    "required": ["id", "key", "display_name", "state_type", "transitions"],
    "additionalProperties": False,
}

_EDGE_ITEM = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "source": {"type": "string"},
        "target": {"type": "string"},
    },
    "required": ["id", "source", "target"],
    "additionalProperties": False,
}

# {
#   "lifecycle_graph_node_id": "aoa...Entity:lifecycle:status",
#   "host_entity_type_qualname": "aoa...Entity",
#   "field_name": "status",
#   "lifecycle_class_qualname": "aoa...OrderLifecycle",
#   "initial_state_keys": ["new"],
#   "states": [
#     {"id": "aoa...Entity:lifecycle:status:new", "key": "new", "display_name": "New", "state_type": "initial", "transitions": ["confirmed"]}
#   ],
#   "transitions": [{"id": "<new id>|lifecycle_transition|<confirmed id>|new", "source": "new", "target": "confirmed"}]
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
