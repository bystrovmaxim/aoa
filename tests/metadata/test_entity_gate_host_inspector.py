# tests/metadata/test_entity_gate_host_inspector.py
"""Unit tests for EntityGateHostInspector."""

from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity, entity
from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity_gate_host import EntityGateHost
from action_machine.domain.entity_gate_host_inspector import EntityGateHostInspector


class _TestDomain(BaseDomain):
    name = "test"
    description = "Test domain"


class _NoEntityMarker(EntityGateHost):
    pass


@entity(description="Simple entity", domain=_TestDomain)
class _SimpleEntity(BaseEntity):
    id: str = Field(description="Identifier")
    title: str = Field(description="Title")


def test_entity_inspector_returns_none_without_entity_info() -> None:
    assert EntityGateHostInspector.inspect(_NoEntityMarker) is None


def test_entity_inspector_builds_payload_with_entity_metadata() -> None:
    payload = EntityGateHostInspector.inspect(_SimpleEntity)
    assert payload is not None
    assert payload.node_type == "entity"

    data = dict(payload.node_meta)
    assert data["description"] == "Simple entity"
    assert data["domain"] is _TestDomain

    fields = data["fields"]
    names = {entry[0] for entry in fields}
    assert "id" in names
    assert "title" in names

    assert data["relations"] == ()
    assert data["lifecycles"] == ()
