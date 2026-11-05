# packages/aoa-action-machine/tests/action_machine/domain/test_entity_private_attributes.py
"""
An entity reads its private attributes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 13.1 of issue #414. ``BaseEntity.__getattr__`` hands every name that is not a
declared field to Pydantic, which keeps private attributes in ``__pydantic_private__``;
a declared field a partial entity does not hold still raises ``FieldNotLoadedError``,
and an unknown name still raises ``AttributeError``.
"""

from __future__ import annotations

import pytest
from pydantic import Field, PrivateAttr

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.exceptions import FieldNotLoadedError
from aoa.action_machine.intents.entity import entity

from ...support.domain_model.domains import TestStorage


@entity(description="An order with a private attribute", resource=TestStorage)
class PrivateSourceOrderCoreEntity(BaseCoreEntity):
    """Keeps where it came from in a private attribute."""

    id: str = Field(description="Order id")
    total: float = Field(default=0.0, description="Total")
    _source: str = PrivateAttr(default="storage")


def test_a_full_entity_reads_its_private_attribute() -> None:
    """Case 13.1: before, AttributeError; now the default."""
    order = PrivateSourceOrderCoreEntity(id="o1")
    assert order.__pydantic_private__ == {"_source": "storage"}
    assert order._source == "storage"


def test_a_partial_entity_reads_its_private_attribute() -> None:
    """The same for a partial entity."""
    assert PrivateSourceOrderCoreEntity.partial(id="o1")._source == "storage"


def test_a_declared_field_a_partial_entity_does_not_hold_still_raises() -> None:
    """The hand-over is for names that are not declared fields."""
    with pytest.raises(FieldNotLoadedError):
        _ = PrivateSourceOrderCoreEntity.partial(id="o1").total


def test_an_unknown_name_still_raises_attribute_error() -> None:
    """Pydantic refuses a name it does not know."""
    with pytest.raises(AttributeError, match="_missing"):
        _ = PrivateSourceOrderCoreEntity(id="o1")._missing
