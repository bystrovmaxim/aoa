# packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle_json_form.py
"""
A lifecycle field goes out as its current status's reference and comes back as the declared status.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 5.1 (the schema), 5.2, 5.3 and 5.4 of issue #407. In JSON mode a lifecycle
writes ``{"code", "display_name", "properties"}``; it reads ``{"code"}`` in every
mode and selects the declared status of its template, so a status read back is
the catalogue's object, not a snapshot of it.
"""

from __future__ import annotations

import json

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseStateEntity, Lifecycle, value
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class _LifecycleFormsDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "lifecycle_json_forms"
    description = "Entities for the lifecycle JSON form tests"


@meta(description="Stores the lifecycle forms entities", domain=_LifecycleFormsDomain)
class _LifecycleFormsStorage(BaseStorage):
    """Hold the lifecycle forms entities."""


@entity(description="Order state", resource=_LifecycleFormsStorage)
class FormOrderStateEntity(BaseStateEntity):
    """Statuses with their own fields, one of them a mutable list."""

    receipt_required: bool = Field(default=False, description="Receipt required")
    labels: list[str] = Field(default_factory=list, description="Labels")
    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Payment received", receipt_required=True)


class FormOrderLifecycle(Lifecycle[FormOrderStateEntity]):
    """A draft order is paid, then it is done."""

    _template = (
        Lifecycle()
        .state(FormOrderStateEntity.DRAFT)
        .to(FormOrderStateEntity.PAID)
        .initial()
        .state(FormOrderStateEntity.PAID)
        .final()
    )


@entity(description="Order", resource=_LifecycleFormsStorage)
class FormStatefulOrderCoreEntity(BaseCoreEntity):
    """An order with a lifecycle, and one that may have none."""

    id: str = Field(description="Order id")
    lifecycle: FormOrderLifecycle = Field(description="State")
    previous: FormOrderLifecycle | None = Field(default=None, description="Previous state")


def _order(state: str = "draft") -> FormStatefulOrderCoreEntity:
    return FormStatefulOrderCoreEntity(id="o1", lifecycle=FormOrderLifecycle(state))


# ── 5.1 and 5.3: JSON out and the schema ───────────────────────────────────


def test_a_lifecycle_goes_out_as_its_status_reference() -> None:
    """Case 5.1/5.3: code, label and the status's own fields under properties."""
    assert _order("paid").model_dump(mode="json")["lifecycle"] == {
        "code": "paid",
        "display_name": "Payment received",
        "properties": {"receipt_required": True, "labels": []},
    }


def test_a_python_dump_keeps_the_lifecycle() -> None:
    """Python mode keeps the lifecycle object."""
    assert isinstance(_order().model_dump()["lifecycle"], FormOrderLifecycle)


def test_the_status_dump_and_the_reference_shape_are_independent() -> None:
    """Case 5.3: the status's own model_dump() stays flat."""
    assert FormOrderStateEntity.PAID.model_dump(mode="json") == {
        "code": "paid",
        "display_name": "Payment received",
        "receipt_required": True,
        "labels": [],
    }


def test_the_schema_builds_with_the_templates_codes() -> None:
    """Case 5.1: the schema builds; code is an enum of the template's states."""
    validation = FormStatefulOrderCoreEntity.model_json_schema(mode="validation")["properties"]["lifecycle"]
    assert validation["properties"]["code"]["enum"] == ["draft", "paid"]
    assert validation["required"] == ["code"]
    serialization = FormStatefulOrderCoreEntity.model_json_schema(mode="serialization")["properties"]["lifecycle"]
    assert set(serialization["required"]) == {"code", "display_name", "properties"}


# ── 5.2: JSON in ────────────────────────────────────────────────────────────


def test_a_code_reads_back_from_a_dict_and_from_json() -> None:
    """Case 5.2: {"code": "draft"} is OrderLifecycle("draft") on every path."""
    data = {"id": "o1", "lifecycle": {"code": "draft"}}
    for order in (
        FormStatefulOrderCoreEntity.model_validate(data),
        FormStatefulOrderCoreEntity.model_validate_json(json.dumps(data)),
    ):
        assert order.lifecycle == FormOrderLifecycle("draft")
        assert type(order.lifecycle) is FormOrderLifecycle


def test_the_written_reference_reads_back() -> None:
    """What goes out comes back equal."""
    order = _order("paid")
    assert FormStatefulOrderCoreEntity.model_validate_json(order.model_dump_json()) == order


def test_an_unknown_code_is_refused_naming_the_states() -> None:
    """Case 5.2: "shipped" is not a state of the template."""
    with pytest.raises(ValidationError, match="shipped") as exc_info:
        FormStatefulOrderCoreEntity.model_validate({"id": "o1", "lifecycle": {"code": "shipped"}})
    assert "draft" in str(exc_info.value)
    assert "paid" in str(exc_info.value)


@pytest.mark.parametrize("lifecycle", ["draft", {"display_name": "Draft"}, {"code": "draft", "extra": 1}, 3])
def test_what_is_not_a_status_reference_is_refused(lifecycle: object) -> None:
    """A bare string, a reference without code, an undeclared key and a number are refused."""
    with pytest.raises(ValidationError):
        FormStatefulOrderCoreEntity.model_validate({"id": "o1", "lifecycle": lifecycle})


def test_a_nullable_lifecycle_round_trips_none() -> None:
    """null goes out and comes back as None."""
    order = _order()
    assert order.model_dump(mode="json")["previous"] is None
    assert FormStatefulOrderCoreEntity.model_validate_json(order.model_dump_json()).previous is None


# ── 5.4: the catalogue's object, not a snapshot ────────────────────────────


def test_a_status_read_back_is_the_declared_object() -> None:
    """Case 5.4: reading back selects the declared status; its fields are the catalogue's now."""
    written = _order("paid").model_dump_json()
    FormOrderStateEntity.PAID.labels.append("changed")
    try:
        back = FormStatefulOrderCoreEntity.model_validate_json(written)
        assert back.lifecycle.current_status is FormOrderStateEntity.PAID
        assert back.lifecycle.current_status.labels == ["changed"]
    finally:
        FormOrderStateEntity.PAID.labels.clear()
