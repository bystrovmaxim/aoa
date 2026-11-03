# packages/maxitor/web/maxitor/web/model/diagrams/actions/events_explorer_action_schema.py
"""JSON Schema for the events explorer's wire JSON (spec 055)."""

from __future__ import annotations

from aoa.action_machine.model import JsonSchemaValue

_STRING = {"type": "string"}


def _object(**properties: object) -> dict[str, object]:
    """A closed object whose every property is required."""
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


_DOMAIN = _object(id=_STRING, label=_STRING, short_label=_STRING, accent_color=_STRING, vocabulary={"type": "boolean"})
_ACTION = _object(id=_STRING, label=_STRING, short_label=_STRING, domain_id=_STRING)
_FIELD = _object(name=_STRING, type=_STRING, description=_STRING)
_EVENT = _object(id=_STRING, label=_STRING, fields={"type": "array", "items": _FIELD})
_HOLD = _object(domain_id=_STRING, event_id=_STRING)
_EMIT = _object(action_id=_STRING, method_id=_STRING, method=_STRING, kind=_STRING, event_id=_STRING)

EventsExplorerJson = JsonSchemaValue.define(
    name="EventsExplorerJson",
    schema=_object(
        domains={"type": "array", "items": _DOMAIN},
        actions={"type": "array", "items": _ACTION},
        events={"type": "array", "items": _EVENT},
        holds={"type": "array", "items": _HOLD},
        emits={"type": "array", "items": _EMIT},
    ),
)
