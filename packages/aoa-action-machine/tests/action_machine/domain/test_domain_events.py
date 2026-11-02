# packages/aoa-action-machine/tests/action_machine/domain/test_domain_events.py
"""
``events`` — what a domain may declare as its vocabulary.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pins the declaration on the domain class. What it means at runtime is in
``runtime/test_emission_rules.py``, and what it means at build in the graph tests.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.model.base_event import BaseEvent


class FirstEvent(BaseEvent):
    """One fact."""


class SecondEvent(BaseEvent):
    """Another fact."""


class ParentDomain(BaseDomain):
    """A domain with a vocabulary."""

    name = "parent"
    description = "Parent"
    events = (FirstEvent,)


class InheritingDomain(ParentDomain):
    """A child keeping the vocabulary."""

    name = "inheriting"
    description = "Inheriting"


class ReplacingDomain(ParentDomain):
    """A child with a vocabulary of its own."""

    name = "replacing"
    description = "Replacing"
    events = (SecondEvent,)


class SharingDomain(BaseDomain):
    """A second domain allowing the same fact."""

    name = "sharing"
    description = "Sharing"
    events = (FirstEvent,)


class SilentDomain(BaseDomain):
    """A domain that emits nothing."""

    name = "silent"
    description = "Silent"
    events = ()


def _define(events: Any) -> None:
    """Define a domain declaring ``events``."""
    type("BadDomain", (BaseDomain,), {"name": "bad", "description": "Bad", "events": events})


@pytest.mark.parametrize(
    "events",
    [[FirstEvent], (str,), ("FirstEvent",), (FirstEvent(),), (BaseEvent,), (FirstEvent, FirstEvent)],
)
def test_invalid_events_are_refused_when_the_domain_is_defined(events: Any) -> None:
    with pytest.raises(EventContractError):
        _define(events)


def test_a_child_inherits_the_vocabulary() -> None:
    assert InheritingDomain.events == (FirstEvent,)


def test_a_child_replaces_the_vocabulary_by_declaring_its_own() -> None:
    assert ReplacingDomain.events == (SecondEvent,)


def test_one_event_may_be_in_several_domains() -> None:
    assert FirstEvent in ParentDomain.events
    assert FirstEvent in SharingDomain.events


def test_an_empty_tuple_is_a_declaration() -> None:
    assert SilentDomain.events == ()


def test_a_domain_without_events_declares_nothing() -> None:
    class PlainDomain(BaseDomain):
        """No vocabulary."""

        name = "plain"
        description = "Plain"

    assert not hasattr(PlainDomain, "events")
