# packages/aoa-action-machine/tests/action_machine/graph/test_json_form_validator.py
"""
The build refuses a Params or Result that has no JSON Schema, and names the field.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 8.1 of issue #409. Each case gives the validator its nodes directly, so a
broken declaration never reaches the graph the other tests build; one test proves
the graph build runs the check.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Annotated, Any

import pytest
from pydantic import Field, PlainSerializer

from aoa.action_machine.domain import AssociationMany, AssociationOne, BaseCoreEntity, BaseDomain, NoInverse
from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.graph.validators import json_form_validator
from aoa.action_machine.graph.validators.json_form_validator import JsonFormError, validate_json_forms
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.model import BaseParams, BaseResult, JsonSchemaValue


class Opaque:
    """A plain Python class: no JSON form."""


class _JsonFormDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "json_form_validator"
    description = "Entities for the build check tests"


@entity(description="Customer", domain=_JsonFormDomain)
class JsonFormCustomerCoreEntity(BaseCoreEntity):
    """A customer."""

    id: str = Field(description="Customer id")


@entity(description="Order", domain=_JsonFormDomain)
class JsonFormOrderCoreEntity(BaseCoreEntity):
    """An order with relations."""

    id: str = Field(description="Order id")
    customer: Annotated[AssociationOne[JsonFormCustomerCoreEntity], NoInverse()] = Field(description="Customer")
    others: Annotated[AssociationMany[JsonFormCustomerCoreEntity], NoInverse()] = Field(description="Others")


Audit = JsonSchemaValue.define(
    name="JsonFormAudit",
    schema={
        "type": "object",
        "properties": {"actor": {"type": "string"}},
        "required": ["actor"],
        "additionalProperties": False,
    }
)
_WIRE = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"], "additionalProperties": False}


class DescribedResult(BaseResult):
    """Every field has a JSON form."""

    audit: Audit = Field(description="Audit")
    order: JsonFormOrderCoreEntity = Field(description="Order")
    summary: JsonFormOrderCoreEntity.schema(schema=_WIRE) = Field(description="Summary")  # type: ignore[valid-type]
    orders: list[JsonFormOrderCoreEntity] = Field(default_factory=list, description="Orders")


def _opaque_action() -> type:
    """Declare, inside a test, the action the messages name: a broken class at module level would reach every build."""

    class OpaqueAction:
        """Holds the Params and Result the messages name, as an action does."""

        class Result(BaseResult):
            """A Result with a field of a plain class."""

            label: str = Field(description="Label")
            raw: Opaque = Field(description="Opaque value")

        class Params(BaseParams):
            """Params with a field of a plain class."""

            raw: Opaque = Field(description="Opaque value")

    return OpaqueAction


def _nodes(*hosts: Any) -> list[SimpleNamespace]:
    return [SimpleNamespace(node_obj=host) for host in hosts]


def test_a_result_field_without_a_json_form_is_named() -> None:
    """Case 8.1: the build refuses the Result and names OpaqueAction.Result.raw."""
    opaque_action: Any = _opaque_action()
    with pytest.raises(JsonFormError, match=r"\.OpaqueAction\.Result\.raw has no JSON form") as caught:
        validate_json_forms(_nodes(opaque_action.Result))
    assert "JsonSchemaValue" in str(caught.value)
    assert isinstance(caught.value, InvalidGraphError)


def test_a_params_field_without_a_json_form_is_named() -> None:
    """Params follow the same rule."""
    opaque_action: Any = _opaque_action()
    with pytest.raises(JsonFormError, match=r"\.OpaqueAction\.Params\.raw has no JSON form"):
        validate_json_forms(_nodes(opaque_action.Params))


def test_a_field_without_a_json_form_in_serialization_mode_is_refused() -> None:
    """A field read fine but written as a plain class is refused too."""

    class WritesOpaqueResult(BaseResult):
        """Read as an int, written as a plain class: no JSON form in serialization mode only."""

        count: Annotated[int, PlainSerializer(lambda value: Opaque(), return_type=Opaque)] = Field(description="Count")

    with pytest.raises(JsonFormError, match=r"\.WritesOpaqueResult\.count has no JSON form \(serialization mode\)"):
        validate_json_forms(_nodes(WritesOpaqueResult))


def test_schema_values_entities_projections_and_relations_pass() -> None:
    """Every type AOA gives a JSON form passes, and a node that is not a Params or Result is skipped."""
    validate_json_forms(_nodes(DescribedResult, JsonFormOrderCoreEntity, _opaque_action(), lambda: None))


def test_the_graph_build_runs_this_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """The coordinator calls the check on every build."""

    def refuse(nodes: Any) -> None:
        raise JsonFormError("the build asked")

    monkeypatch.setattr(json_form_validator, "validate_json_forms", refuse)
    with pytest.raises(JsonFormError, match="the build asked"):
        create_node_graph_coordinator()
