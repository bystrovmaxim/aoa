# packages/aoa-action-machine/tests/action_machine/runtime/test_emission_rules_in_a_domain.py
"""
What a method may write in a domain with ``events``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mode 3: a line with no event and an event outside the vocabulary are refused for every
kind of method, a method without ``@emits`` writes nothing, and each method answers to its
own domain.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AccessUndecided
from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.exceptions.on_error_handler_error import OnErrorHandlerError
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.model import BaseAction, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.emission_rules import EmissionRules, emission_rules_for
from aoa.action_machine.runtime.tools_box import ToolsBox

from .emission_support import (
    KINDS,
    ListedEvent,
    UnlistedEvent,
    _machine,
    _Params,
    _params,
    _RecordingLogger,
    _Result,
    _say,
)
from .test_emission_rules import _PlainAction

# ── A domain with events ─────────────────────────────────────────────────────


class _VocabularyDomain(BaseDomain):
    """A domain allowing one event."""

    name = "vocabulary"
    description = "Vocabulary"
    events = (ListedEvent,)


class _ClosedDomain(BaseDomain):
    """A domain that emits nothing."""

    name = "closed"
    description = "Closed"
    events = ()


@meta(description="All five kinds of method, no @emits, in a typed domain", domain=_VocabularyDomain)
@check_roles(GuestRole)
class _UndeclaredAction(BaseAction[_Params, _Result]):
    """A method without ``@emits`` writes nothing in a typed domain."""

    @access_decide("Allow")
    async def undeclared_access_decide(self, params: _Params, box: ToolsBox, connections: Connections) -> Verdict:
        """Speak, then allow."""
        await _say(box, params, "access")
        return Allowed()

    @regular_aspect("First")
    async def first_aspect(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Speak."""
        await _say(box, params, "regular")
        return {}

    @compensate(first_aspect, "Undo the first step")
    async def first_compensate(
        self,
        params: _Params,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        """Speak."""
        await _say(box, params, "compensate")

    @regular_aspect("Second")
    async def second_aspect(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Fail when asked."""
        if params.fail:
            raise ValueError("planned")
        return {}

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _Result:
        """Speak."""
        await _say(box, params, "summary")
        return _Result(outcome="summary")

    @on_error(ValueError, description="Answer for the planned failure")
    async def planned_on_error(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections, error: ValueError
    ) -> _Result:
        """Speak."""
        await _say(box, params, "handler")
        return _Result(outcome="handler")


@meta(description="A declared event from the vocabulary", domain=_VocabularyDomain)
@check_roles(GuestRole)
class _DeclaredAction(BaseAction[_Params, _Result]):
    """Its summary emits what it declares, and it may run an action from an untyped domain."""

    @summary_aspect("Finish")
    @emits(ListedEvent)
    async def finish_summary(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _Result:
        """Speak, or run a nested action that writes as before."""
        await _say(box, params, "summary")
        if params.speaker == "nested":
            await box.run(_PlainAction, _Params(speaker="summary", write="kwargs"))
        return _Result(outcome="summary")


@meta(description="A domain that emits nothing", domain=_ClosedDomain)
@check_roles(GuestRole)
class _ClosedAction(BaseAction[_Params, _Result]):
    """Any line of it is refused."""

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _Result:
        """Speak."""
        await _say(box, params, "summary")
        return _Result(outcome="summary")


async def _assert_refused(machine: ActionProductMachine, kind: str, write: str) -> None:
    """Run one kind of method and assert that it failed by its own path."""
    params = _params(kind, write)
    if kind in ("regular", "summary"):
        with pytest.raises(EventContractError):
            await machine.run(Context(), _UndeclaredAction(), params)
    elif kind == "handler":
        with pytest.raises(OnErrorHandlerError):
            await machine.run(Context(), _UndeclaredAction(), params)
    elif kind == "access":
        with pytest.raises(AccessUndecided):
            await machine.run(Context(), _UndeclaredAction(), params)
    else:
        assert (await machine.run(Context(), _UndeclaredAction(), params)).outcome == "handler"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("write", ["kwargs", "plain", "listed", "unlisted"])
async def test_in_a_typed_domain_a_method_without_emits_writes_nothing(kind: str, write: str) -> None:
    logger = _RecordingLogger()

    await _assert_refused(_machine(logger), kind, write)

    assert not logger.lines


@pytest.mark.parametrize("write", ["kwargs", "plain", "unlisted"])
async def test_in_a_typed_domain_a_method_with_emits_keeps_to_its_list(write: str) -> None:
    logger = _RecordingLogger()

    with pytest.raises(EventContractError):
        await _machine(logger).run(Context(), _DeclaredAction(), _Params(speaker="summary", write=write))

    assert not logger.lines


async def test_in_a_typed_domain_a_declared_event_is_delivered() -> None:
    logger = _RecordingLogger()

    await _machine(logger).run(Context(), _DeclaredAction(), _Params(speaker="summary", write="listed"))

    assert logger.messages() == ["listed o1"]


@pytest.mark.parametrize("write", ["kwargs", "plain", "listed"])
async def test_an_empty_vocabulary_refuses_everything(write: str) -> None:
    logger = _RecordingLogger()

    with pytest.raises(EventContractError):
        await _machine(logger).run(Context(), _ClosedAction(), _Params(speaker="summary", write=write))

    assert not logger.lines


async def test_a_nested_action_answers_to_its_own_domain() -> None:
    logger = _RecordingLogger()

    await _machine(logger).run(Context(), _DeclaredAction(), _Params(speaker="nested"))

    assert logger.messages() == ["kwargs 1"]
    assert type(logger.lines[0].var) is dict


def test_an_event_outside_the_vocabulary_is_refused_even_when_declared() -> None:
    rules = EmissionRules("ShopAction", "pay_aspect", (UnlistedEvent,), (ListedEvent,), "vocabulary")

    with pytest.raises(EventContractError, match="vocabulary"):
        rules.check(UnlistedEvent())


def test_an_action_with_no_domain_answers_to_emits_only() -> None:
    class NoDomainAction(BaseAction[_Params, _Result]):
        """An action with no ``@meta``."""

        @summary_aspect("Finish")
        @emits(ListedEvent)
        async def finish_summary(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> _Result:
            """Answer."""
            return _Result(outcome="summary")

        @regular_aspect("Plain")
        async def plain_aspect(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> dict[str, Any]:
            """Stay out of every rule."""
            return {}

    assert emission_rules_for(NoDomainAction, "plain_aspect") is None
    rules = emission_rules_for(NoDomainAction, "finish_summary")
    assert rules is not None and rules.vocabulary is None


def test_a_domain_with_no_events_has_no_rules_for_a_plain_method() -> None:
    assert emission_rules_for(_PlainAction, "finish_summary") is None
