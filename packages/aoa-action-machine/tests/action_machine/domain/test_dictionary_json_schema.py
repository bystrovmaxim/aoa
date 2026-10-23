# tests/action_machine/domain/test_dictionary_json_schema.py
"""
Tests for the two JSON schemas of a dictionary-typed field.

The contract has two sides and they are not the same shape. The input schema must
accept what the runtime accepts — a code-only reference, a reference with a stale
label, a full reference — and refuse what the runtime refuses. The output schema
must describe what the framework emits: three members, and every extra property
typed by what the serializer produces, not by the Python field it came from.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field, ValidationError, field_serializer

from aoa.action_machine.domain import BaseEnumEntity, value
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


@exclude_graph_model
class SchemaCurrencyEnumEntity(BaseEnumEntity):
    """A dictionary with one extra property."""

    symbol: str = Field(description="Currency symbol")

    EUR = value(code="eur", display_name="Euro", symbol="€")


@exclude_graph_model
class SchemaDatedEnumEntity(BaseEnumEntity):
    """A dictionary whose date field is formatted by its own serializer."""

    since: date = Field(description="Start date")

    ITEM = value(code="item", display_name="Item", since=date(2020, 1, 2))

    @field_serializer("since")
    def serialize_since(self, moment: date) -> str:
        """Format the date for consumers."""
        return moment.strftime("%d/%m/%Y")


class SchemaInvoice(BaseModel):
    """Reference both dictionaries, so both schemas are generated."""

    currency: SchemaCurrencyEnumEntity
    dated: SchemaDatedEnumEntity


def _validation_errors(payload: dict) -> list[str]:
    """Validate a payload against the holder's input schema."""
    schema = SchemaInvoice.model_json_schema(mode="validation")
    return [error.message for error in Draft202012Validator(schema).iter_errors(payload)]


_FULL = {"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}}
_DATED = {"code": "item", "display_name": "Item", "properties": {"since": "02/01/2020"}}


@pytest.mark.parametrize("currency", [{"code": "eur"}, {"code": "eur", "display_name": "Euro"}, _FULL])
def test_the_input_schema_accepts_what_the_runtime_accepts(currency: dict) -> None:
    """A code-only reference, a labelled one and a full one all validate on the input side."""
    assert _validation_errors({"currency": currency, "dated": _DATED}) == []
    validated = SchemaInvoice.model_validate({"currency": currency, "dated": _DATED})
    assert validated.currency is SchemaCurrencyEnumEntity.EUR


def test_the_input_schema_refuses_a_blank_code() -> None:
    """A blank code is refused by the schema and by the runtime alike."""
    errors = _validation_errors({"currency": {"code": ""}, "dated": _DATED})
    assert errors and errors[0] == "'' should be non-empty"
    with pytest.raises(ValidationError):
        SchemaInvoice.model_validate({"currency": {"code": ""}, "dated": _DATED})


def test_the_input_schema_refuses_an_extra_member() -> None:
    """Only `code`, `display_name` and `properties` may enter, exactly as the runtime requires."""
    payload = {"currency": {"code": "eur", "symbol": "€"}, "dated": _DATED}
    assert any("Additional properties are not allowed" in message for message in _validation_errors(payload))


def test_the_input_schema_keeps_properties_open() -> None:
    """The runtime ignores what a payload carries under `properties`, so the input schema does too."""
    assert _validation_errors({"currency": {"code": "eur", "properties": {"anything": [1, 2]}}, "dated": _DATED}) == []


def _reference_schema(mode: str, field: str = "currency") -> dict:
    """Return the generated schema of one dictionary-typed field in one mode."""
    return SchemaInvoice.model_json_schema(mode=mode)["properties"][field]


def test_the_output_schema_requires_all_three_members() -> None:
    """The emitted reference is complete: code, label and properties."""
    schema = _reference_schema("serialization")

    assert schema["required"] == ["code", "display_name", "properties"]
    assert schema["additionalProperties"] is False


def test_the_output_schema_types_each_property() -> None:
    """Each extra property appears by name, with its emitted type, and nothing else may appear."""
    properties = _reference_schema("serialization")["properties"]["properties"]

    assert properties["additionalProperties"] is False
    assert properties["properties"] == {"symbol": {"type": "string"}}


def test_the_output_schema_describes_the_serializer_not_the_python_field() -> None:
    """A date with a serializer is a plain string in the output schema — no stale `format`."""
    properties = _reference_schema("serialization", "dated")["properties"]["properties"]

    assert properties["properties"]["since"] == {"type": "string"}


def test_the_output_schema_introduces_no_reference_to_another_definition() -> None:
    """The supported property types are scalars and tuples, so the emitted object carries no `$ref`."""
    properties = _reference_schema("serialization")["properties"]["properties"]

    assert "$ref" not in json.dumps(properties)


def test_each_mode_enters_the_hook_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generating a schema enters the hook once; the serialization branch cannot re-enter it."""
    calls: list[str] = []

    @exclude_graph_model
    class RecordedEnumEntity(BaseEnumEntity):
        """A fresh dictionary, built while the hook is instrumented."""

        symbol: str = Field(description="Currency symbol")

        EUR = value(code="eur", display_name="Euro", symbol="€")

    original = BaseEnumEntity.__get_pydantic_json_schema__.__func__

    def counting(cls: type, schema: dict, handler: object) -> dict:
        """Record the mode, then delegate to the real hook."""
        calls.append(handler.mode)  # type: ignore[attr-defined]
        return original(cls, schema, handler)  # type: ignore[arg-type]

    monkeypatch.setattr(BaseEnumEntity, "__get_pydantic_json_schema__", classmethod(counting))
    monkeypatch.setattr(RecordedEnumEntity, "__get_pydantic_json_schema__", classmethod(counting))

    class RecordedHolder(BaseModel):
        """A holder built after the patch, so its core schema captures the counting hook."""

        recorded: RecordedEnumEntity

    calls.clear()
    RecordedHolder.model_json_schema(mode="serialization")
    assert calls == ["serialization"]

    calls.clear()
    RecordedHolder.model_json_schema(mode="validation")
    assert calls == ["validation"]


def test_the_runtime_still_refuses_what_the_schema_does_not_describe() -> None:
    """The input schema is not the enforcement: unknown codes and copied values still fail at runtime."""
    with pytest.raises(ValidationError, match="not a declared value"):
        SchemaInvoice.model_validate({"currency": {"code": "bootleg"}, "dated": _DATED})
    with pytest.raises(ValidationError, match="copy of a declared value"):
        SchemaInvoice.model_validate({"currency": SchemaCurrencyEnumEntity(code="eur", display_name="Copy", symbol="?"), "dated": _DATED})
