# tests/action_machine/domain/test_entity_schema_pydantic.py
"""
Pydantic v2 integration for ``BaseEntity.schema()`` / :class:`~aoa.action_machine.domain.entity_schema_marker.EntitySchemaMarker`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

PR-2: runtime validation, JSON Schema emission, and unchanged behavior for full
``BaseEntity`` models without ``.schema(...)``.
"""

from __future__ import annotations

import pytest

from tests.action_machine.adapters.entity_projection_adapter_fixtures import EntityProjectionAdapterTestAction
from tests.action_machine.scenarios.domain_model.entities import SampleEntity


class TestEntityProjectionResultValidation:
    """``BaseResult`` fields annotated with ``BaseEntity.schema(...)`` validate wire dicts."""

    def test_accepts_valid_projection_dict(self) -> None:
        payload = {"domain": "Billing", "order": {"id": "e1", "name": "One"}}
        result = EntityProjectionAdapterTestAction.Result.model_validate(payload)
        assert result.domain == "Billing"
        assert result.order == {"id": "e1", "name": "One"}

    def test_rejects_missing_required_property(self) -> None:
        payload = {"domain": "Billing", "order": {"id": "e1"}}
        with pytest.raises(ValueError, match="wire projection"):
            EntityProjectionAdapterTestAction.Result.model_validate(payload)

    def test_rejects_extra_property_when_additional_properties_false(self) -> None:
        payload = {
            "domain": "Billing",
            "order": {"id": "e1", "name": "One", "extra": 1},
        }
        with pytest.raises(ValueError, match="wire projection"):
            EntityProjectionAdapterTestAction.Result.model_validate(payload)

    def test_validator_returns_same_dict_object(self) -> None:
        order = {"id": "e1", "name": "One"}
        payload = {"domain": "Billing", "order": order}
        result = EntityProjectionAdapterTestAction.Result.model_validate(payload)
        assert result.order is order


class TestEntityProjectionJsonSchema:
    """``model_json_schema`` exposes the inline wire schema for projection fields."""

    def test_order_property_matches_marker_schema(self) -> None:
        schema = EntityProjectionAdapterTestAction.Result.model_json_schema()
        order_prop = schema["properties"]["order"]
        assert order_prop.get("type") == "object"
        assert set(order_prop.get("required", [])) == {"id", "name"}
        assert order_prop["properties"]["id"] == {"type": "string"}
        assert order_prop["properties"]["name"] == {"type": "string"}
        assert order_prop.get("additionalProperties") is False


class TestPlainBaseEntityUnchanged:
    """Full entity models without ``.schema(...)`` keep standard Pydantic behavior."""

    def test_sample_entity_still_validates_as_entity(self) -> None:
        entity = SampleEntity.model_validate({"id": "1", "name": "A", "value": 0})
        assert entity.id == "1"
        assert entity.name == "A"
        assert entity.value == 0
