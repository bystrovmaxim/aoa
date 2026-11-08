# packages/aoa-action-machine/tests/action_machine/domain/test_entity_partial_loading.py
"""
A partial entity holds only what was loaded.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 2.1–2.3 of issue #405. ``partial()`` sets only the given fields: no default
and no default factory of another field runs, an unloaded field is never read
or dumped, and ``model_copy(update=...)`` makes the updated fields loaded.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import Field, PrivateAttr

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
from aoa.action_machine.domain.exceptions import FieldNotLoadedError
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage

_factory_calls: list[str] = []


def _counted_note() -> str:
    """Return a note and record that the factory ran."""
    _factory_calls.append("note")
    return "none"


class _PartialDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "partial_loading"
    description = "Entities for the partial loading tests"


@meta(description="Stores the partial entities")
class _PartialStorage(BaseStorage):
    """Hold the partial entities."""


@entity(description="Order", domain=_PartialDomain)
class PartialOrderCoreEntity(BaseCoreEntity):
    """An order whose fields have a default, a factory that needs the id, and a counting factory."""

    id: str = Field(description="Order id")
    total: float = Field(default=0.0, description="Total")
    currency: str = Field(default="RUB", description="Currency")
    code: str = Field(default_factory=lambda data: data["id"].upper(), description="Code made from the id")
    note: str = Field(default_factory=_counted_note, description="Note")

    _source: str = PrivateAttr(default="storage")


def _full() -> PartialOrderCoreEntity:
    return PartialOrderCoreEntity(id="o1", total=2.0, currency="EUR", code="O1", note="n")


# ── 2.1: an unloaded field with a default ──────────────────────────────────


def test_an_unloaded_field_with_a_default_is_not_readable() -> None:
    """Case 2.1: reading currency of partial(id) raises FieldNotLoadedError, not 'RUB'."""
    order = PartialOrderCoreEntity.partial(id="o1")
    with pytest.raises(FieldNotLoadedError) as exc_info:
        _ = order.currency
    assert exc_info.value.loaded_fields == frozenset({"id"})
    assert not order.is_field_loaded("currency")


@pytest.mark.parametrize("mode", ["python", "json"])
def test_an_unloaded_field_is_not_dumped(mode: str) -> None:
    """Case 2.1: the dump holds the loaded fields only, in both modes."""
    assert PartialOrderCoreEntity.partial(id="o1").model_dump(mode=mode) == {"id": "o1"}


def test_get_field_value_of_an_unloaded_field_raises() -> None:
    """get_field_value never returns the default of an unloaded field."""
    with pytest.raises(FieldNotLoadedError):
        PartialOrderCoreEntity.partial(id="o1").get_field_value("currency")


# ── 2.3: no code of an unloaded field runs ──────────────────────────────────


def test_a_factory_that_needs_a_missing_field_does_not_run() -> None:
    """Case 2.3: partial() without id builds an instance with nothing loaded."""
    order = PartialOrderCoreEntity.partial()
    assert order.model_dump() == {}
    assert not order.is_field_loaded("code")


def test_no_default_factory_runs_for_a_partial() -> None:
    """Case 2.3: the counting factory runs 0 times for partial(id='o1')."""
    _factory_calls.clear()
    PartialOrderCoreEntity.partial(id="o1")
    assert _factory_calls == []


def test_a_full_entity_still_applies_its_defaults() -> None:
    """A validated entity fills every default and runs every factory."""
    _factory_calls.clear()
    order = PartialOrderCoreEntity(id="o1")
    assert (order.currency, order.code, order.note) == ("RUB", "O1", "none")
    assert _factory_calls == ["note"]
    assert all(order.is_field_loaded(name) for name in PartialOrderCoreEntity.model_fields)


# ── equality ────────────────────────────────────────────────────────────────


def test_a_partial_with_every_field_equals_the_full_entity() -> None:
    """A partial given every field is indistinguishable from the full entity."""
    full = _full()
    partial = PartialOrderCoreEntity.partial(**full.model_dump())
    assert partial == full
    assert all(partial.is_field_loaded(name) for name in PartialOrderCoreEntity.model_fields)


def test_a_partial_with_some_fields_differs_from_the_full_entity() -> None:
    """A partial with fewer fields is not equal to the full entity."""
    assert PartialOrderCoreEntity.partial(id="o1") != _full()


# ── 2.2: model_copy(update=...) ─────────────────────────────────────────────


def test_an_updated_field_becomes_loaded() -> None:
    """Case 2.2: model_copy(update=...) reports the updated field loaded; the rest stay unloaded."""
    order = PartialOrderCoreEntity.partial(id="o1").model_copy(update={"total": 2.0})
    assert order.is_field_loaded("total")
    assert order.total == 2.0
    with pytest.raises(FieldNotLoadedError):
        _ = order.currency


# ── construction against Pydantic ───────────────────────────────────────────


def test_a_partial_sets_the_slots_pydantic_sets() -> None:
    """The instance holds exactly the given fields and the class's private defaults."""
    order: Any = PartialOrderCoreEntity.partial(id="o1", total=1.0)
    assert order.__dict__ == {"id": "o1", "total": 1.0}
    assert order.model_fields_set == {"id", "total"}
    assert order.__pydantic_extra__ is None
    assert order.__pydantic_private__ == {"_source": "storage"}
