# packages/aoa-action-machine/tests/action_machine/model/test_base_event.py
"""
BaseEvent — what a typed fact allows and refuses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pins the event as a class: its fields, its name, the names it may not use, and that a
dump holds the fact and nothing about how a line was delivered.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.model.base_event import BaseEvent

SYSTEM_FIELDS = ("level", "channels", "domain", "domain_name")
READ_METHODS = ("get", "keys", "values", "items", "resolve")


class OrderCompletedEvent(BaseEvent):
    """A fact with two fields."""

    order_id: str
    total: float


class ShippedOrderEvent(OrderCompletedEvent):
    """A fact adding a field to an intermediate event class."""

    carrier: str


def test_a_wrong_type_is_refused() -> None:
    with pytest.raises(ValidationError):
        OrderCompletedEvent(order_id="o1", total="many")  # type: ignore[arg-type]


def test_an_extra_field_is_refused() -> None:
    with pytest.raises(ValidationError):
        OrderCompletedEvent(order_id="o1", total=1.0, extra=1)  # type: ignore[call-arg]


def test_a_built_event_cannot_be_changed() -> None:
    event = OrderCompletedEvent(order_id="o1", total=1.0)
    with pytest.raises(ValidationError):
        event.order_id = "o2"  # type: ignore[misc]


def test_a_name_without_the_suffix_is_refused() -> None:
    with pytest.raises(NamingSuffixError):
        type("OrderCompleted", (BaseEvent,), {"__annotations__": {"order_id": str}})


@pytest.mark.filterwarnings("error")
@pytest.mark.parametrize("name", SYSTEM_FIELDS + READ_METHODS)
def test_a_reserved_field_name_is_refused(name: str) -> None:
    with pytest.raises(EventContractError, match=name):
        type("ReservedNameEvent", (BaseEvent,), {"__annotations__": {name: str}, name: "x"})


@pytest.mark.parametrize("name", SYSTEM_FIELDS)
def test_an_author_cannot_set_a_system_field(name: str) -> None:
    with pytest.raises(ValidationError, match=name):
        OrderCompletedEvent(order_id="o1", total=1.0, **{name: None})


def test_a_built_event_has_empty_system_fields() -> None:
    event = OrderCompletedEvent(order_id="o1", total=1.0)
    assert [getattr(event, name) for name in SYSTEM_FIELDS] == [None] * 4


def test_a_dump_holds_every_field_except_the_system_ones() -> None:
    event = ShippedOrderEvent(order_id="o1", total=1.0, carrier="post")
    assert event.model_dump() == {"order_id": "o1", "total": 1.0, "carrier": "post"}
