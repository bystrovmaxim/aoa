# packages/maxitor/web/maxitor/web/model/diagrams/actions/domain_events_diagram_action_schema.py
"""JSON Schema for the events diagram's wire JSON (spec 053)."""

from __future__ import annotations

from aoa.action_machine.model import JsonSchemaValue

_STRING = {"type": "string"}

_DOMAIN = {
    "type": "object",
    "properties": {"id": _STRING, "label": _STRING, "short_label": _STRING, "accent_color": _STRING, "typed_events": {"type": ["boolean", "null"]}},
    "required": ["id", "label", "short_label", "accent_color", "typed_events"],
    "additionalProperties": False,
}

_ACTION = {
    "type": "object",
    "properties": {"id": _STRING, "label": _STRING, "short_label": _STRING, "domain_id": _STRING, "domain_short_label": _STRING, "accent_color": _STRING},
    "required": ["id", "label", "short_label", "domain_id", "domain_short_label", "accent_color"],
    "additionalProperties": False,
}

_METHOD = {
    "type": "object",
    "properties": {"id": _STRING, "label": _STRING, "kind": _STRING, "action_id": _STRING},
    "required": ["id", "label", "kind", "action_id"],
    "additionalProperties": False,
}

_FIELD = {
    "type": "object",
    "properties": {"name": _STRING, "type": _STRING, "description": _STRING},
    "required": ["name", "type", "description"],
    "additionalProperties": False,
}

_PRODUCER = {
    "type": "object",
    "properties": {"id": _STRING, "label": _STRING, "kind": _STRING, "action_id": _STRING, "action_label": _STRING},
    "required": ["id", "label", "kind", "action_id", "action_label"],
    "additionalProperties": False,
}

_EVENT_DOMAIN = {
    "type": "object",
    "properties": {"id": _STRING, "label": _STRING, "in_vocabulary": {"type": "boolean"}},
    "required": ["id", "label", "in_vocabulary"],
    "additionalProperties": False,
}

_EVENT = {
    "type": "object",
    "properties": {
        "id": _STRING,
        "label": _STRING,
        "band": {"type": "string", "enum": ["in_vocabulary", "not_emitted", "emitted"]},
        "fields": {"type": "array", "items": _FIELD},
        "methods": {"type": "array", "items": _PRODUCER},
        "domains": {"type": "array", "items": _EVENT_DOMAIN},
    },
    "required": ["id", "label", "band", "fields", "methods", "domains"],
    "additionalProperties": False,
}

_EDGE = {
    "type": "object",
    "properties": {"id": _STRING, "edge_kind": {"type": "string", "enum": ["method", "emits"]}, "source_id": _STRING, "target_id": _STRING},
    "required": ["id", "edge_kind", "source_id", "target_id"],
    "additionalProperties": False,
}

DomainEventsDiagramJson = JsonSchemaValue.define(
    name="DomainEventsDiagramJson",
    schema={
        "type": "object",
        "properties": {
            "domain": _DOMAIN,
            "actions": {"type": "array", "items": _ACTION},
            "methods": {"type": "array", "items": _METHOD},
            "events": {"type": "array", "items": _EVENT},
            "edges": {"type": "array", "items": _EDGE},
        },
        "required": ["domain", "actions", "methods", "events", "edges"],
        "additionalProperties": False,
    },
)
