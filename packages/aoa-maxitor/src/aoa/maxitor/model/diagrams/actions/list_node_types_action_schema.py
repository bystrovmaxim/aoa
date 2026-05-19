# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_node_types_action_schema.py
"""
list_node_types_action_schema — JSON Schema for ``ListNodeTypesAction.Result.list_node_types``.
"""

from __future__ import annotations

from aoa.action_machine.model import JsonSchemaValue

# Graph ``nodes.type`` value with one G6 disk fill hex per row.
ListNodeTypesJson = JsonSchemaValue.define(
    name="ListNodeTypesJson",
    schema={
        "type": "array",
        "minItems": 0,
        "items": {
            "type": "object",
            "properties": {
                "node_type": {"type": "string"},
                "color": {"type": "string"},
            },
            "required": ["node_type", "color"],
            "additionalProperties": False,
        },
    },
)
