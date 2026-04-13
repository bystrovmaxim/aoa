# tests/graph/test_sensitive_intent_inspector.py
"""Unit tests for SensitiveIntentInspector."""

from __future__ import annotations

from action_machine.graph.inspectors.sensitive_intent_inspector import SensitiveIntentInspector
from action_machine.intents.logging import sensitive
from action_machine.model.base_schema import BaseSchema


class _NoSensitiveSchema(BaseSchema):
    value: str


class _BaseSensitiveSchema(BaseSchema):
    _secret: str

    @property
    @sensitive(True, max_chars=2, char="*", max_percent=50)
    def secret(self) -> str:
        return self._secret


class _ChildSensitiveSchema(_BaseSensitiveSchema):
    pass


def test_sensitive_inspector_returns_none_without_sensitive_fields() -> None:
    assert SensitiveIntentInspector.inspect(_NoSensitiveSchema) is None


def test_sensitive_inspector_builds_payload_with_inherited_fields() -> None:
    payload = SensitiveIntentInspector.inspect(_ChildSensitiveSchema)
    assert payload is not None
    assert payload.node_type == "sensitive"

    data = dict(payload.node_meta)
    fields = data["sensitive_fields"]
    assert len(fields) == 1
    fd = dict(fields[0])
    assert fd["property_name"] == "secret"
    config = fd["config"]
    assert ("enabled", True) in config
    assert ("max_chars", 2) in config
