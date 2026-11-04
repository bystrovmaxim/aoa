# packages/aoa-action-machine/tests/action_machine/domain/test_projection_holds_entity.py
"""
A projection holds the entity: a partial entity with exactly the projection's fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 6.1–6.3 of issue #408. A field declared with ``Entity.schema(schema=...)``
takes a full entity, a partial one or a dict, checks the value by the
projection's schema and by the entity's field types, and holds
``Entity.partial(...)`` with exactly the projection's fields; a projection names
only fields of its entity.
"""

from __future__ import annotations

import json
import re
from typing import Annotated

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseDomain, NoInverse
from aoa.action_machine.domain.exceptions import FieldNotLoadedError
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult


class _ProjectionDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "projection_holds_entity"
    description = "Entities for the projection tests"


@entity(description="Customer", domain=_ProjectionDomain)
class ProjCustomerCoreEntity(BaseCoreEntity):
    """A customer."""

    id: str = Field(description="Customer id")


@entity(description="Order", domain=_ProjectionDomain)
class ProjOrderCoreEntity(BaseCoreEntity):
    """An order with fields inside and outside the projection."""

    id: str = Field(description="Order id")
    status: str = Field(description="Status")
    total: float = Field(ge=0, description="Total")
    customer_email: str = Field(description="Email")
    customer: Annotated[AssociationOne[ProjCustomerCoreEntity], NoInverse()] = Field(description="Customer")


@entity(description="Another entity", domain=_ProjectionDomain)
class ProjInvoiceCoreEntity(BaseCoreEntity):
    """An entity of another class with the same field names."""

    id: str = Field(description="Invoice id")
    status: str = Field(description="Status")
    total: float = Field(description="Total")


ORDER_WIRE = {
    "type": "object",
    "properties": {"id": {"type": "string"}, "status": {"type": "string"}, "total": {"type": "number"}},
    "required": ["id", "status", "total"],
    "additionalProperties": False,
}


class ProjSummaryResult(BaseResult):
    """A Result with a projection field."""

    order: ProjOrderCoreEntity.schema(schema=ORDER_WIRE) = Field(description="Order row")  # type: ignore[valid-type]


class ProjSummaryParams(BaseParams):
    """Params with a projection field."""

    order: ProjOrderCoreEntity.schema(schema=ORDER_WIRE) = Field(description="Order row")  # type: ignore[valid-type]


class ProjMaybeResult(BaseResult):
    """A Result with an optional projection field."""

    order: ProjOrderCoreEntity.schema(schema=ORDER_WIRE) | None = Field(default=None, description="Order row")  # type: ignore[valid-type]


ROW = {"id": "o1", "status": "paid", "total": 99.5}


def _order() -> ProjOrderCoreEntity:
    return ProjOrderCoreEntity(
        id="o1",
        status="paid",
        total=99.5,
        customer_email="ann@example.com",
        customer=AssociationOne[ProjCustomerCoreEntity](id="c1"),
    )


# ── 6.1: returning an entity through a projection ──────────────────────────


def test_a_full_entity_is_returned_through_a_projection() -> None:
    """Case 6.1: the projection takes the entity and keeps exactly its fields."""
    result = ProjSummaryResult(order=_order())
    assert result.model_dump(mode="json") == {"order": ROW}
    assert result.order.status == "paid"
    assert type(result.order) is ProjOrderCoreEntity
    with pytest.raises(FieldNotLoadedError):
        _ = result.order.customer_email


@pytest.mark.parametrize(
    "given",
    [ProjOrderCoreEntity.partial(**ROW), ROW],
    ids=["partial", "dict"],
)
def test_a_partial_entity_or_a_dict_gives_the_same_partial(given: object) -> None:
    """A partial holding the fields, or a dict of them, gives the same projection."""
    held = ProjSummaryResult(order=given).order
    assert held == ProjOrderCoreEntity.partial(**ROW)
    assert {name for name in ProjOrderCoreEntity.model_fields if held.is_field_loaded(name)} == set(ROW)


def test_a_partial_without_a_required_field_is_refused_by_name() -> None:
    """A value missing a field the projection requires is refused, naming it."""
    with pytest.raises(ValidationError, match="'total' is a required property"):
        ProjSummaryResult(order=ProjOrderCoreEntity.partial(id="o1", status="paid"))


def test_a_python_dump_gives_the_projections_fields() -> None:
    """Python mode dumps the projected entity as any nested model: a dict of the fields it holds."""
    assert ProjSummaryResult(order=_order()).model_dump()["order"] == ROW


def test_an_optional_projection_keeps_none() -> None:
    """A `| None` projection holds None as it is."""
    assert ProjMaybeResult(order=None).order is None
    assert ProjMaybeResult(order=_order()).order.id == "o1"


def test_an_entity_of_another_class_is_refused() -> None:
    """A projection of an order does not take an invoice."""
    with pytest.raises(ValidationError):
        ProjSummaryResult(order=ProjInvoiceCoreEntity(id="i1", status="paid", total=1.0))


# ── 6.2: a projection on input ─────────────────────────────────────────────


def test_a_projection_on_input_is_an_entity() -> None:
    """Case 6.2: Params from a dict and from JSON hold a partial entity with attribute and key reads."""
    for params in (
        ProjSummaryParams.model_validate({"order": ROW}),
        ProjSummaryParams.model_validate_json(json.dumps({"order": ROW})),
    ):
        assert type(params.order) is ProjOrderCoreEntity
        assert params.order.id == "o1"
        assert params.order["id"] == "o1"


def test_each_value_is_checked_by_the_fields_own_type() -> None:
    """Case 6.2: the schema takes a negative total, the entity's field (ge=0) does not."""
    with pytest.raises(
        ValidationError, match=re.escape("ProjOrderCoreEntity.total: Input should be greater than or equal to 0")
    ):
        ProjSummaryParams.model_validate({"order": {"id": "o1", "status": "paid", "total": -1}})


def test_the_schema_still_checks_the_value() -> None:
    """A value the projection's schema refuses is refused with today's wording."""
    with pytest.raises(ValidationError, match="ProjOrderCoreEntity wire projection: 'total' is a required property"):
        ProjSummaryParams.model_validate({"order": {"id": "o1", "status": "paid"}})


# ── 6.3: a projection names only fields of its entity ──────────────────────


def test_a_schema_naming_a_field_the_entity_lacks_is_refused() -> None:
    """Case 6.3: `secret` is not a field of the order, so the projection is refused when declared."""
    leak = {
        "type": "object",
        "properties": {"id": {"type": "string"}, "secret": {"type": "string"}},
        "required": ["id", "secret"],
        "additionalProperties": False,
    }
    with pytest.raises(ValueError, match="secret") as exc_info:
        ProjOrderCoreEntity.schema(schema=leak)
    assert "ProjOrderCoreEntity" in str(exc_info.value)


_EIGHT = [f"f{i}" for i in range(8)]


@entity(description="Eight fields, enough that a hash order rarely matches the declared one", domain=_ProjectionDomain)
class ProjWideCoreEntity(BaseCoreEntity):
    """An entity with eight string fields."""

    id: str = Field(description="Id")
    f0: str = Field(description="Field 0")
    f1: str = Field(description="Field 1")
    f2: str = Field(description="Field 2")
    f3: str = Field(description="Field 3")
    f4: str = Field(description="Field 4")
    f5: str = Field(description="Field 5")
    f6: str = Field(description="Field 6")
    f7: str = Field(description="Field 7")


_WIDE_WIRE = {
    "type": "object",
    "properties": {name: {"type": "string"} for name in reversed(_EIGHT)},
    "required": list(reversed(_EIGHT)),
    "additionalProperties": False,
}


class WideResult(BaseResult):
    """Return the projection of the eight fields."""

    row: ProjWideCoreEntity.schema(schema=_WIDE_WIRE) = Field(description="Row")  # type: ignore[valid-type]


def test_the_json_of_a_projection_follows_the_entity_field_order() -> None:
    """JSON keys come in the entity's declaration order, from an entity and from a reversed dict alike."""
    values = {name: name.upper() for name in _EIGHT}
    from_entity = WideResult(row=ProjWideCoreEntity(id="w1", **values))
    from_dict = WideResult(row=dict(reversed(list(values.items()))))
    assert list(from_entity.model_dump(mode="json")["row"]) == _EIGHT
    assert list(from_dict.model_dump(mode="json")["row"]) == _EIGHT
