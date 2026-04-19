# tests/graph/test_sensitive_intent_inspector.py
"""Unit tests for SensitiveIntentInspector."""

from __future__ import annotations

from action_machine.legacy.sensitive_intent_inspector import SensitiveIntentInspector
from action_machine.logging import sensitive
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


def test_sensitive_inspector_emits_field_vertices_and_host_edges() -> None:
    payloads = SensitiveIntentInspector.inspect(_ChildSensitiveSchema)
    assert payloads is not None
    field_nodes = [p for p in payloads if p.node_type == "sensitive_field"]
    assert len(field_nodes) == 1
    sf = field_nodes[0]
    assert sf.node_name.endswith(":secret")
    meta = dict(sf.node_meta)
    assert meta["property_name"] == "secret"
    assert ("enabled", True) in meta["config"]

    host_payloads = [
        p for p in payloads if p.node_type == "described_fields" and p.node_class is _BaseSensitiveSchema
    ]
    assert len(host_payloads) == 1
    host = host_payloads[0]
    assert len(host.edges) == 1
    e = host.edges[0]
    assert e.edge_type == "has_sensitive_field"
    assert e.target_node_type == "sensitive_field"
    assert e.target_name == sf.node_name
