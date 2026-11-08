# tests/action_machine/domain/test_dictionary_association_schema.py
"""
Tests for the two schema modes of an explicit dictionary association.

The validation schema describes the two accepted inputs, the ``{id: code}`` object and
the reference read by its code; the serialization schema describes the emitted dictionary
reference. JSON output is the canonical member's ``to_reference()``.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

import pytest
from pydantic import Field, ValidationError, field_serializer

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    NoInverse,
    value,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class SchemaDomain(BaseDomain):
    """Domain for dictionary-association schema fixtures."""

    name = "association-schema"
    description = "Association schema"


@meta(description="Stores the schema entities")
class SchemaStorage(BaseStorage):
    """Hold the schema entities."""


@entity(description="Dated currency", domain=SchemaDomain)
class DatedCurrencyEnumEntity(BaseEnumEntity):
    """A dictionary whose date field carries its own serializer."""

    since: date = Field(description="Start date")

    ITEM = value(code="item", display_name="Item", since=date(2020, 1, 2))

    @field_serializer("since")
    def serialize_since(self, moment: date) -> str:
        """Format the date for consumers."""
        return moment.strftime("%d/%m/%Y")


@exclude_graph_model
@entity(description="Host", domain=SchemaDomain)
class HostCoreEntity(BaseCoreEntity):
    """A host selecting a dated dictionary value."""

    id: str = Field(description="Identifier")
    dated: Annotated[AssociationOne[DatedCurrencyEnumEntity], NoInverse()] = Field(description="Dated")
    optional: Annotated[AssociationOne[DatedCurrencyEnumEntity] | None, NoInverse()] = Field(
        default=None, description="Optional"
    )


def test_json_input_accepts_the_id_object() -> None:
    """A JSON ``{id: code}`` object resolves to the canonical member."""
    host = HostCoreEntity.model_validate_json('{"id": "h1", "dated": {"id": "item"}}')

    assert host.dated.entity is DatedCurrencyEnumEntity.ITEM


def test_json_input_with_extra_keys_is_refused() -> None:
    """The transport container carries only ``id``."""
    with pytest.raises(ValidationError, match="exactly one 'id' key"):
        HostCoreEntity.model_validate_json('{"id": "h2", "dated": {"id": "item", "extra": 1}}')


def test_the_reference_written_is_read_back_by_its_code() -> None:
    """The reference a relation writes is accepted back; the catalogue supplies label and properties."""
    host = HostCoreEntity.model_validate_json(
        '{"id": "h3", "dated": {"code": "item", "display_name": "Other", "properties": {}}}'
    )

    assert host.dated.entity is DatedCurrencyEnumEntity.ITEM
    assert host.dated.entity.display_name == "Item"


def test_a_reference_with_an_undeclared_key_is_refused() -> None:
    """A reference carries only code, display_name and properties."""
    with pytest.raises(ValidationError, match="a dictionary relation takes"):
        HostCoreEntity.model_validate_json('{"id": "h6", "dated": {"code": "item", "extra": 1}}')


def test_json_output_equals_to_reference() -> None:
    """JSON output is the member's existing reference, including its custom serializer."""
    host = HostCoreEntity.model_validate_json('{"id": "h4", "dated": {"id": "item"}}')

    assert host.model_dump(mode="json")["dated"] == DatedCurrencyEnumEntity.ITEM.to_reference()
    assert host.model_dump(mode="json")["dated"]["properties"]["since"] == "02/01/2020"


def test_a_nullable_absence_emits_null() -> None:
    """An absent nullable selection serializes to null."""
    host = HostCoreEntity.model_validate_json('{"id": "h5", "dated": {"id": "item"}}')

    assert host.model_dump(mode="json")["optional"] is None


def test_the_validation_schema_describes_both_inputs() -> None:
    """The validation schema offers the id object and the reference read by its code."""
    schema = HostCoreEntity.model_json_schema(mode="validation")

    id_object, reference = schema["properties"]["dated"]["anyOf"]
    assert id_object["required"] == ["id"]
    assert set(id_object["properties"]) == {"id"}
    assert reference["required"] == ["code"]
    assert set(reference["properties"]) == {"code", "display_name", "properties"}


def test_the_serialization_schema_describes_the_reference() -> None:
    """The serialization schema is the emitted reference, not the container input."""
    schema = HostCoreEntity.model_json_schema(mode="serialization")

    dated = schema["properties"]["dated"]
    assert set(dated["required"]) == {"code", "display_name", "properties"}
    assert set(dated["properties"]) == {"code", "display_name", "properties"}
