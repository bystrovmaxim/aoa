# packages/aoa-action-machine/tests/action_machine/domain/test_entity_field_takes_full.py
"""
A field typed by an entity carries a full entity; a partial one goes through a projection.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 6.4 of issue #408. A field typed by the bare entity, by ``Entity | None`` or
by ``list[Entity]`` refuses a partial entity, so a response never omits a field
its own published schema requires; the message names what the entity holds and
points to a projection.
"""

from __future__ import annotations

import re

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity, value
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.resources.base_storage import BaseStorage


class _FullDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "entity_field_takes_full"
    description = "Entities for the full-entity field tests"


@meta(description="Stores the full entities")
class _FullStorage(BaseStorage):
    """Hold the full entities."""


@entity(description="Order", domain=_FullDomain)
class FullPlainOrderCoreEntity(BaseCoreEntity):
    """An order with two fields."""

    id: str = Field(description="Id")
    total: float = Field(description="Total")


@entity(description="Currencies", domain=_FullDomain)
class FullCurrencyEnumEntity(BaseEnumEntity):
    """A dictionary: its values are never partial."""

    EUR = value(code="eur", display_name="Euro")


class FullOrderResult(BaseResult):
    """Fields typed by the entity in the three shapes, and a dictionary."""

    order: FullPlainOrderCoreEntity = Field(description="Order")
    maybe: FullPlainOrderCoreEntity | None = Field(default=None, description="Maybe an order")
    many: list[FullPlainOrderCoreEntity] = Field(default_factory=list, description="Orders")
    currency: FullCurrencyEnumEntity = Field(default=FullCurrencyEnumEntity.EUR, description="Currency")


FULL = FullPlainOrderCoreEntity(id="o1", total=2.0)
PARTIAL = FullPlainOrderCoreEntity.partial(id="o2")
MESSAGE = (
    "FullPlainOrderCoreEntity is partial (loaded: id); this field takes a full entity. "
    "Declare a projection with FullPlainOrderCoreEntity.schema(...)."
)


def test_a_full_entity_is_accepted() -> None:
    """A full entity is accepted in every shape, as today."""
    result = FullOrderResult(order=FULL, maybe=FULL, many=[FULL])
    assert result.order is FULL
    assert result.model_dump(mode="json")["order"] == {"id": "o1", "total": 2.0}


@pytest.mark.parametrize(
    "fields",
    [{"order": PARTIAL}, {"order": FULL, "maybe": PARTIAL}, {"order": FULL, "many": [FULL, PARTIAL]}],
    ids=["bare", "optional", "list"],
)
def test_a_partial_entity_is_refused(fields: dict[str, object]) -> None:
    """Case 6.4: a partial entity is refused, naming what it holds and pointing to a projection."""
    with pytest.raises(ValidationError, match=re.escape(MESSAGE)):
        FullOrderResult(**fields)


def test_a_dict_with_every_field_still_builds_a_full_entity() -> None:
    """Validation from a dict fills the entity as it always did."""
    assert FullOrderResult.model_validate({"order": {"id": "o3", "total": 1.0}}).order.total == 1.0


def test_a_dictionary_value_is_unaffected() -> None:
    """A dictionary's values are never partial; a field typed by the dictionary works as before."""
    assert FullOrderResult(order=FULL).currency is FullCurrencyEnumEntity.EUR
