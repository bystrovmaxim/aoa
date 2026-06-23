# tests/action_machine/domain/test_entity_schema_projection.py
"""
Tests for ``BaseEntity.schema()`` and :class:`~aoa.action_machine.domain.entity_schema_marker.EntitySchemaMarker`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers PR-1 marker construction and PR-2 helper ``entity_schema_marker_from_annotated``.
Pydantic/OpenAPI wiring is covered in ``test_entity_schema_pydantic`` and adapter tests.
"""

from __future__ import annotations

from typing import Annotated, Any, get_args, get_origin

import pytest

from aoa.action_machine.domain.entity_schema_marker import EntitySchemaMarker, entity_schema_marker_from_annotated
from tests.action_machine.scenarios.domain_model.entities import SampleEntity


def _marker_from_alias(alias: Any) -> EntitySchemaMarker:
    assert get_origin(alias) is Annotated
    meta = get_args(alias)[1:]
    markers = [m for m in meta if isinstance(m, EntitySchemaMarker)]
    assert len(markers) == 1
    return markers[0]


class TestBaseEntitySchema:
    """``BaseEntity.schema()`` returns ``Annotated`` with a single ``EntitySchemaMarker``."""

    def test_schema_returns_annotated_with_marker(self) -> None:
        wire_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "value": {"type": "integer"},
            },
            "required": ["id", "name", "value"],
            "additionalProperties": False,
        }
        alias = SampleEntity.schema(schema=wire_schema)
        assert get_origin(alias) is Annotated
        args = get_args(alias)
        assert args[0] is SampleEntity
        marker = _marker_from_alias(alias)
        assert marker.entity_cls is SampleEntity
        assert marker.schema == wire_schema
        assert marker.schema is not wire_schema

    def test_entity_schema_marker_from_annotated_matches_manual_extraction(self) -> None:
        wire_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
            "additionalProperties": False,
        }
        alias = SampleEntity.schema(schema=wire_schema)
        assert entity_schema_marker_from_annotated(alias) is _marker_from_alias(alias)

    def test_entity_schema_marker_from_annotated_plain_type_returns_none(self) -> None:
        assert entity_schema_marker_from_annotated(str) is None
        assert entity_schema_marker_from_annotated(dict[str, object]) is None

    def test_schema_rejects_non_dict(self) -> None:
        with pytest.raises(TypeError, match="schema must be a dict"):
            SampleEntity.schema(schema="not-a-dict")  # type: ignore[arg-type]

    def test_schema_rejects_empty_dict(self) -> None:
        with pytest.raises(ValueError, match="schema cannot be empty"):
            SampleEntity.schema(schema={})
