# tests/action_machine/model/test_json_schema_value.py
"""
Tests for JsonSchemaValue — schema-backed JSON fields on BaseResult.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers validation, serialization, JSON Schema emission, optional fields,
``model_construct`` limitations, and ``define()``-time schema checks per PR-1.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import jsonschema
import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.model import JsonSchemaValue
from aoa.action_machine.model.base_result import BaseResult

PERSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name"],
    "additionalProperties": False,
}
PersonJson = JsonSchemaValue.define(name="PersonJson", schema=PERSON_SCHEMA)


class PersonResult(BaseResult):
    label: str
    person: PersonJson


def _resolve_schema_node(root: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """Follow a single-level ``#/$defs/Name`` ref; otherwise return ``node``."""
    ref = node.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        return node
    key = ref.removeprefix("#/$defs/")
    defs = root.get("$defs", {})
    if key not in defs:
        return node
    return defs[key]


def _field_json_schema(model: type[BaseResult], field_name: str) -> dict[str, Any]:
    root = model.model_json_schema()
    prop = root["properties"][field_name]
    return _resolve_schema_node(root, prop)


def test_valid_object_passes() -> None:
    result = PersonResult(label="x", person={"name": "Alice", "age": 30})
    assert result.person == {"name": "Alice", "age": 30}


def test_missing_required_field_raises() -> None:
    with pytest.raises(ValidationError):
        PersonResult(label="x", person={"age": 30})


def test_wrong_type_raises() -> None:
    with pytest.raises(ValidationError):
        PersonResult(label="x", person={"name": 123})


def test_additional_property_raises() -> None:
    with pytest.raises(ValidationError):
        PersonResult(label="x", person={"name": "Alice", "extra": 1})


def test_non_json_object_raises() -> None:
    with pytest.raises(ValidationError):
        PersonResult(label="x", person=datetime.now())  # type: ignore[arg-type]


def test_model_dump_returns_raw_dict() -> None:
    result = PersonResult(label="x", person={"name": "Alice", "age": 30})
    dumped = result.model_dump()["person"]
    assert dumped == {"name": "Alice", "age": 30}
    assert type(dumped) is dict


def test_model_dump_json_returns_raw_json() -> None:
    result = PersonResult(label="x", person={"name": "Alice", "age": 30})
    assert json.loads(result.model_dump_json())["person"] == {"name": "Alice", "age": 30}


def test_model_json_schema_contains_field_schema() -> None:
    person_schema = _field_json_schema(PersonResult, "person")
    assert person_schema.get("required") == ["name"]
    assert "name" in person_schema["properties"]


class PersonDescribedResult(BaseResult):
    label: str
    person: PersonJson = Field(description="Person payload")


def test_field_description_preserved() -> None:
    root = PersonDescribedResult.model_json_schema()
    assert root["properties"]["person"].get("description") == "Person payload"


def test_no_arbitrary_types_allowed_needed() -> None:
    """JsonSchemaValue validates via hooks; callers need no extra ``model_config`` for this field."""
    assert PersonResult(label="ok", person={"name": "Bob"}).model_dump()["person"]["name"] == "Bob"


def test_input_schema_not_mutated() -> None:
    schema_copy = dict(PERSON_SCHEMA)
    _ = JsonSchemaValue.define(name="PersonJsonCopy", schema=schema_copy)
    PersonResult.model_json_schema()
    assert schema_copy == PERSON_SCHEMA
    assert PERSON_SCHEMA["properties"]["name"] == {"type": "string"}


def test_two_types_have_independent_schemas() -> None:
    shared: dict[str, Any] = {
        "type": "object",
        "properties": {"k": {"type": "string"}},
        "required": ["k"],
        "additionalProperties": False,
    }
    t_a = JsonSchemaValue.define(name="IndepA", schema=shared)
    t_b = JsonSchemaValue.define(name="IndepB", schema=shared)
    assert t_a._json_schema is not t_b._json_schema
    assert t_a._json_schema == t_b._json_schema


class OptionalPersonResult(BaseResult):
    person: PersonJson | None = None


def test_optional_field_accepts_none() -> None:
    assert OptionalPersonResult(person=None).model_dump()["person"] is None


def test_optional_field_validates_when_not_none() -> None:
    with pytest.raises(ValidationError):
        OptionalPersonResult(person={"age": 30})


def test_model_construct_skips_validation() -> None:
    bad = PersonResult.model_construct(label="x", person={"invalid": True})
    assert bad.model_dump()["person"] == {"invalid": True}


def test_define_validates_schema_itself() -> None:
    with pytest.raises(jsonschema.exceptions.SchemaError):
        JsonSchemaValue.define(name="Bad", schema={"type": "notavalidtype"})


LIST_SCHEMA: dict[str, Any] = {"type": "array", "items": {"type": "string"}}
TagsJson = JsonSchemaValue.define(name="TagsJson", schema=LIST_SCHEMA)


class TagsResult(BaseResult):
    label: str
    tags: TagsJson


def test_list_value_passes() -> None:
    r = TagsResult(label="t", tags=["a", "b"])
    assert r.model_dump()["tags"] == ["a", "b"]
