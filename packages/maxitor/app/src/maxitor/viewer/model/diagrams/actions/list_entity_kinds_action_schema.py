# packages/maxitor/app/src/maxitor/viewer/model/diagrams/actions/list_entity_kinds_action_schema.py
"""
list_entity_kinds_action_schema — JSON Schema for ``ListEntityKindsAction.Result.list_entity_kinds``.
"""

from __future__ import annotations

from aoa.action_machine.model import JsonSchemaValue

# One row per entity kind present in the loaded graph: its word and the name a reader sees.
ListEntityKindsJson = JsonSchemaValue.define(
    name="ListEntityKindsJson",
    schema={
        "type": "array",
        "minItems": 0,
        "items": {
            "type": "object",
            "properties": {
                "entity_kind": {"type": "string", "minLength": 1},
                "label": {"type": "string", "minLength": 1},
            },
            "required": ["entity_kind", "label"],
            "additionalProperties": False,
        },
    },
)
