# packages/aoa-action-machine/tests/action_machine/graph/test_emits_vocabulary_validator.py
"""
The build holds every ``@emits`` of a domain to the domain's ``events``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each case gives the validator one action, so a broken declaration never reaches the
graph the other tests build.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.graph.validators import emits_vocabulary_validator
from aoa.action_machine.graph.validators.emits_vocabulary_validator import validate_emits_vocabulary
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_event import BaseEvent


class AllowedEvent(BaseEvent):
    """In the vocabulary."""


class SparedEvent(BaseEvent):
    """In the vocabulary, and nobody declares it."""


class OutsideEvent(BaseEvent):
    """Outside the vocabulary."""


class ShopDomain(BaseDomain):
    """A domain with a vocabulary."""

    name = "shop"
    description = "Shop"
    events = (AllowedEvent, SparedEvent)


class OpenDomain(BaseDomain):
    """A domain with no vocabulary."""

    name = "open"
    description = "Open"


class _Params(BaseParams):
    """Nothing to pass."""


class _Result(BaseResult):
    """Nothing to answer."""


def _action(kind: str, event: type[BaseEvent], domain: type[BaseDomain]) -> type[Any]:
    """Build an action with one declared method of ``kind``."""

    @regular_aspect("Step")
    async def step_aspect(self: Any, params: Any, state: Any, box: Any, connections: Any) -> dict[str, Any]:
        """A step."""
        return {}

    @regular_aspect("Declared")
    async def declared_aspect(self: Any, params: Any, state: Any, box: Any, connections: Any) -> dict[str, Any]:
        """The regular kind."""
        return {}

    @summary_aspect("Declared")
    async def declared_summary(self: Any, params: Any, state: Any, box: Any, connections: Any) -> _Result:
        """The summary kind."""
        return _Result()

    @compensate(step_aspect, "Declared")
    async def declared_compensate(
        self: Any, params: Any, state_before: Any, state_after: Any, box: Any, connections: Any, error: Any
    ) -> None:
        """The compensator kind."""

    @on_error(ValueError, description="Declared")
    async def declared_on_error(self: Any, params: Any, state: Any, box: Any, connections: Any, error: Any) -> _Result:
        """The handler kind."""
        return _Result()

    @access_decide("Declared")
    async def declared_access_decide(self: Any, params: Any, box: Any, connections: Any) -> Any:
        """The access kind."""
        return None

    methods = {
        "regular": declared_aspect,
        "summary": declared_summary,
        "compensate": declared_compensate,
        "handler": declared_on_error,
        "access": declared_access_decide,
    }
    method = emits(event)(methods[kind])

    class OneMethodAction(BaseAction[_Params, _Result]):
        """Takes its one declared method below."""

    setattr(OneMethodAction, method.__name__, method)
    return meta(description="One declared method", domain=domain)(OneMethodAction)


@pytest.mark.parametrize("kind", ["regular", "summary", "compensate", "handler", "access"])
def test_an_event_outside_the_vocabulary_fails_the_build(kind: str) -> None:
    action = _action(kind, OutsideEvent, ShopDomain)

    with pytest.raises(EventContractError) as refused:
        validate_emits_vocabulary([SimpleNamespace(node_obj=action)])

    assert "OutsideEvent" in str(refused.value)
    assert "declared" in str(refused.value)
    assert "shop" in str(refused.value)


@pytest.mark.parametrize("kind", ["regular", "summary", "compensate", "handler", "access"])
def test_an_event_from_the_vocabulary_passes(kind: str) -> None:
    validate_emits_vocabulary([SimpleNamespace(node_obj=_action(kind, AllowedEvent, ShopDomain))])


def test_a_domain_with_no_events_is_not_looked_at() -> None:
    validate_emits_vocabulary([SimpleNamespace(node_obj=_action("summary", OutsideEvent, OpenDomain))])


def test_a_node_that_is_no_action_is_skipped() -> None:
    validate_emits_vocabulary([SimpleNamespace(node_obj=OpenDomain), SimpleNamespace(node_obj=lambda: None)])


def test_the_graph_build_runs_this_check(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(nodes: Any) -> None:
        raise EventContractError("the build asked")

    monkeypatch.setattr(emits_vocabulary_validator, "validate_emits_vocabulary", refuse)

    with pytest.raises(EventContractError, match="the build asked"):
        create_node_graph_coordinator()
