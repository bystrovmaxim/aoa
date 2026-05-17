# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/domain_use_case_diagram_action_schema.py
"""JSON Schema for :class:`GetDomainUseCaseDiagramAction.Result` (use-case diagram wire JSON)."""

from __future__ import annotations

from aoa.action_machine.model import JsonSchemaValue

_DOMAIN = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "label": {"type": "string"},
        "short_label": {"type": "string"},
        "accent_color": {"type": "string"},
    },
    "required": ["id", "label", "short_label", "accent_color"],
    "additionalProperties": False,
}

_ACTION = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "label": {"type": "string"},
        "short_label": {"type": "string"},
        "domain_id": {"type": "string"},
        "domain_short_label": {"type": "string"},
        "accent_color": {"type": "string"},
        "role_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "id",
        "label",
        "short_label",
        "domain_id",
        "domain_short_label",
        "accent_color",
        "role_ids",
    ],
    "additionalProperties": False,
}

_ROLE = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "label": {"type": "string"},
        "short_label": {"type": "string"},
    },
    "required": ["id", "label", "short_label"],
    "additionalProperties": False,
}

_EDGE = {
    "type": "object",
    "properties": {
        "edge_kind": {
            "type": "string",
            "enum": [
                "action_generalization",
                "role_generalization",
                "association",
                "include",
                "extend",
                "depends",
            ],
        },
        "source_id": {"type": "string"},
        "target_id": {"type": "string"},
        "stereotype": {"type": ["string", "null"]},
    },
    "required": ["edge_kind", "source_id", "target_id"],
    "additionalProperties": False,
}

DomainUseCaseDiagramJson = JsonSchemaValue.define(
    name="DomainUseCaseDiagramJson",
    schema={
        "type": "object",
        "properties": {
            "domain": _DOMAIN,
            "actions": {"type": "array", "items": _ACTION},
            "roles": {"type": "array", "items": _ROLE},
            "edges": {"type": "array", "items": _EDGE},
        },
        "required": ["domain", "actions", "roles", "edges"],
        "additionalProperties": False,
    },
)
