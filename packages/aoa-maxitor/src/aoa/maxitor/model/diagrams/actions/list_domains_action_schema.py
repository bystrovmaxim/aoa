# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_domains_action_schema.py
"""
list_domains_action_schema — JSON Schema for ``ListDomainsAction.Result.list_domains``.
"""

from __future__ import annotations

from aoa.action_machine.model import JsonSchemaValue

# Ordered interchange ``BaseDomain`` type qualnames with one ERD accent hex per row.
ListDomainsJson = JsonSchemaValue.define(
    name="ListDomainsJson",
    schema={
        "type": "array",
        "minItems": 0,
        "items": {
            "type": "object",
            "properties": {
                "qualname": {"type": "string"},
                "label": {"type": "string"},
                "color": {"type": "string"},
            },
            "required": ["qualname", "label", "color"],
            "additionalProperties": False,
        },
    },
)
