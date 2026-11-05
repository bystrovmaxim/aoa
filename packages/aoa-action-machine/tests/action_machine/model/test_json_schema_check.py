# packages/aoa-action-machine/tests/action_machine/model/test_json_schema_check.py
"""
A JSON Schema check is built once, in the draft it checks values with.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 6.5 of issue #406, through the two kinds of schema field: a
``JsonSchemaValue`` field and an entity projection (``BaseEntity.schema``). The
schema is checked at declaration in the draft its ``$schema`` names (the newest
one without it); a value check checks only the value and reports the error
``jsonschema.validate`` reports today.
"""

from __future__ import annotations

import copy
import pickle
import subprocess
import sys
import warnings
from collections.abc import Iterator
from typing import Annotated, Any

import jsonschema
import pytest
from jsonschema.validators import Draft7Validator, Draft202012Validator
from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
from aoa.action_machine.domain.entity_schema_marker import EntitySchemaMarker
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.json_schema_value import JsonSchemaValue
from aoa.action_machine.resources.base_storage import BaseStorage

ORDER_WIRE: dict[str, Any] = {
    "type": "object",
    "properties": {"id": {"type": "string"}, "status": {"type": "string"}, "total": {"type": "number"}},
    "required": ["id", "status", "total"],
    "additionalProperties": False,
}
PAIR: dict[str, Any] = {"type": "array", "items": [{"type": "string"}, {"type": "integer"}]}
PAIR7: dict[str, Any] = {"$schema": "http://json-schema.org/draft-07/schema#", **PAIR}
# A projection lists fields of its entity (#408), so its Draft 7 tuple form sits inside one of them.
ORDER_PAIR: dict[str, Any] = {
    "type": "object",
    "properties": {"id": {"type": "string", "items": [{"type": "string"}, {"type": "integer"}]}},
    "required": ["id"],
    "additionalProperties": False,
}
ORDER_PAIR7: dict[str, Any] = {"$schema": "http://json-schema.org/draft-07/schema#", **ORDER_PAIR}
UNKNOWN_DRAFT: dict[str, Any] = {"$schema": "http://example.com/unknown-draft", "type": "string"}
TUPLE_REFUSAL = "[{'type': 'string'}, {'type': 'integer'}] is not of type 'object', 'boolean'"
GOOD_ROW = {"id": "o1", "status": "paid", "total": 99.5}
BAD_ROW = {"id": 1, "status": "paid", "secret": "x"}


class _ChecksDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "json_schema_checks"
    description = "Entities for the JSON Schema check tests"


@meta(description="Stores the checks entities", domain=_ChecksDomain)
class _ChecksStorage(BaseStorage):
    """Hold the checks entities."""


@entity(description="Order", resource=_ChecksStorage)
class CheckOrderCoreEntity(BaseCoreEntity):
    """An order projected through a strict schema."""

    id: str = Field(description="Order id")
    status: str = Field(description="Status")
    total: float = Field(description="Total")


Audit = JsonSchemaValue.define(name="Audit", schema=ORDER_WIRE)


class ProjectionResult(BaseResult):
    """A Result with a projection field."""

    order: CheckOrderCoreEntity.schema(schema=ORDER_WIRE) = Field(description="Order row")  # type: ignore[valid-type]


class AuditResult(BaseResult):
    """A Result with a JsonSchemaValue field."""

    audit: Audit = Field(description="Audit")  # type: ignore[valid-type]


def _projection_marker(schema: dict[str, Any]) -> EntitySchemaMarker:
    marker = CheckOrderCoreEntity.schema(schema=schema).__metadata__[0]
    assert isinstance(marker, EntitySchemaMarker)
    return marker


# ── case 6.5: the draft at declaration ─────────────────────────────────────


def test_a_tuple_schema_without_draft_is_refused_by_json_schema_value() -> None:
    """The newest draft refuses a list of items, so the declaration does."""
    with pytest.raises(jsonschema.SchemaError) as exc_info:
        JsonSchemaValue.define(name="Pair", schema=PAIR)
    assert exc_info.value.message == TUPLE_REFUSAL


def test_a_tuple_schema_without_draft_is_refused_by_a_projection() -> None:
    """A projection follows the same rule at declaration."""
    with pytest.raises(jsonschema.SchemaError) as exc_info:
        CheckOrderCoreEntity.schema(schema=ORDER_PAIR)
    assert exc_info.value.message == TUPLE_REFUSAL


def test_a_schema_naming_draft_7_checks_its_values_as_draft_7() -> None:
    """With $schema naming Draft 7 the tuple schema is accepted and checks positions."""
    pair7 = JsonSchemaValue.define(name="Pair7", schema=PAIR7)

    class Pair7Result(BaseResult):
        """A Result with a Draft 7 tuple field."""

        pair: pair7 = Field(description="Pair")  # type: ignore[valid-type]

    assert Pair7Result(pair=["a", 1]).pair == ["a", 1]
    with pytest.raises(ValidationError, match="'a' is not of type 'integer'"):
        Pair7Result(pair=[1, "a"])


def test_a_projection_naming_draft_7_is_accepted() -> None:
    """A projection whose schema names Draft 7 is declared without error."""
    assert _projection_marker(ORDER_PAIR7).schema == ORDER_PAIR7


def test_an_unknown_draft_warns_once_at_declaration() -> None:
    """The newest draft is used for an unknown $schema, with one warning, and no warning per value."""
    with warnings.catch_warnings(record=True) as declared:
        warnings.simplefilter("always")
        word_type = JsonSchemaValue.define(name="Word", schema=UNKNOWN_DRAFT)

        class WordResult(BaseResult):
            """A Result with a field of an unknown draft."""

            word: word_type = Field(description="Word")  # type: ignore[valid-type]

    assert [w.category for w in declared] == [DeprecationWarning]
    with warnings.catch_warnings(record=True) as checked:
        warnings.simplefilter("always")
        for _ in range(3):
            WordResult(word="w")
    assert checked == []


# ── case 6.5: a value check checks only the value ──────────────────────────


@pytest.fixture
def schema_checks(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """Record every check of a schema made by the two drafts in use."""
    calls: list[str] = []
    for cls in (Draft202012Validator, Draft7Validator):
        original = cls.check_schema

        def counting(
            schema: Any, *args: Any, _original: Any = original, _name: str = cls.__name__, **kwargs: Any
        ) -> Any:
            calls.append(_name)
            return _original(schema, *args, **kwargs)

        monkeypatch.setattr(cls, "check_schema", staticmethod(counting))
    yield calls


def test_no_value_check_checks_the_schema(schema_checks: list[str]) -> None:
    """Twenty values through both kinds of field check the schema zero times."""
    for _ in range(5):
        ProjectionResult(order=GOOD_ROW)
        AuditResult(audit=GOOD_ROW)
        with pytest.raises(ValidationError):
            ProjectionResult(order=BAD_ROW)
        with pytest.raises(ValidationError):
            AuditResult(audit=BAD_ROW)
    assert schema_checks == []


# ── case 6.5: the reported error is today's ────────────────────────────────


def _today(value: Any, schema: dict[str, Any]) -> jsonschema.ValidationError:
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=value, schema=schema)
    return exc_info.value


def test_a_projection_reports_the_best_error() -> None:
    """The projection reports the error jsonschema.validate picks, in its own wording."""
    with pytest.raises(ValidationError) as exc_info:
        ProjectionResult(order=BAD_ROW)
    message = exc_info.value.errors()[0]["msg"]
    assert message == "Value error, CheckOrderCoreEntity wire projection: 'total' is a required property"
    assert _today(BAD_ROW, ORDER_WIRE).message == "'total' is a required property"


def test_a_json_schema_value_reports_the_best_error() -> None:
    """A JsonSchemaValue field reports str() of the error jsonschema.validate picks."""
    with pytest.raises(ValidationError) as exc_info:
        AuditResult(audit=BAD_ROW)
    assert exc_info.value.errors()[0]["msg"] == f"Value error, {_today(BAD_ROW, ORDER_WIRE)}"


# ── the marker stays what it is ─────────────────────────────────────────────


def test_two_markers_of_one_schema_are_equal() -> None:
    """Equality and repr of a marker name only its entity and its schema."""
    first, second = _projection_marker(ORDER_WIRE), _projection_marker(ORDER_WIRE)
    assert first == second
    assert repr(first) == f"EntitySchemaMarker(entity_cls={CheckOrderCoreEntity!r}, schema={ORDER_WIRE!r})"


@pytest.mark.parametrize("how", [copy.deepcopy, lambda m: pickle.loads(pickle.dumps(m))], ids=["deepcopy", "pickle"])
def test_a_copied_marker_checks_values_the_same_way(how: Any) -> None:
    """A marker after deepcopy or pickle is equal and accepts and refuses the same values."""
    marker = _projection_marker(ORDER_WIRE)
    copied = how(marker)
    assert copied == marker

    class CopiedResult(BaseResult):
        """A Result whose projection field carries the copied marker."""

        order: Annotated[CheckOrderCoreEntity, copied] = Field(description="Order row")

    assert CopiedResult(order=GOOD_ROW).order.model_dump() == GOOD_ROW
    with pytest.raises(ValidationError, match="'total' is a required property"):
        CopiedResult(order=BAD_ROW)


@pytest.mark.parametrize(
    "module", ["aoa.action_machine.domain.entity_schema_marker", "aoa.action_machine.model.json_schema_value"]
)
def test_each_user_of_the_check_imports_first(module: str) -> None:
    """Either user of the shared check imports cleanly as the first module of a fresh process."""
    done = subprocess.run([sys.executable, "-c", f"import {module}"], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
