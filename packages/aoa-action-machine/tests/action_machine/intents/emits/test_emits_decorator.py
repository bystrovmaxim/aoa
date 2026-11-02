# packages/aoa-action-machine/tests/action_machine/intents/emits/test_emits_decorator.py
"""
@emits — what the declaration accepts, and where it may stand.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pins the declaration alone. What a method with ``@emits`` may write at runtime is in
``runtime/test_emission_rules.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.exceptions.decorator_argument_type_error import DecoratorArgumentTypeError
from aoa.action_machine.exceptions.decorator_argument_value_error import DecoratorArgumentValueError
from aoa.action_machine.exceptions.duplicate_declaration_error import DuplicateDeclarationError
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class _Params(BaseParams):
    """Nothing to pass."""


class _Result(BaseResult):
    """Nothing to answer."""


class FirstEvent(BaseEvent):
    """One fact."""


class SecondEvent(BaseEvent):
    """Another fact."""


def test_nothing_listed_is_refused() -> None:
    with pytest.raises(DecoratorArgumentValueError):
        emits()


@pytest.mark.parametrize("value", [str, "FirstEvent", FirstEvent(), BaseEvent])
def test_anything_but_an_event_class_is_refused(value: Any) -> None:
    with pytest.raises(DecoratorArgumentTypeError):
        emits(value)


def test_a_repeated_event_is_refused() -> None:
    with pytest.raises(DecoratorArgumentValueError):
        emits(FirstEvent, FirstEvent)


def test_a_second_emits_on_one_method_is_refused() -> None:
    with pytest.raises(DuplicateDeclarationError):

        @emits(FirstEvent)
        @emits(SecondEvent)
        async def method() -> None:
            """A method declared twice."""


def _declared(method: Any) -> tuple[type[BaseEvent], ...]:
    """Return what the method declares."""
    return method._emits_events  # pylint: disable=protected-access


def test_emits_may_stand_above_or_below_each_decorator() -> None:
    class AnyOrderAction(BaseAction[_Params, _Result]):
        """All five kinds, ``@emits`` above and below in turn."""

        @emits(FirstEvent)
        @access_decide("Allow")
        async def order_access_decide(self, params: _Params, box: ToolsBox, connections: Connections) -> Verdict:
            """Above."""
            return Allowed()

        @regular_aspect("Above")
        @emits(FirstEvent)
        async def below_aspect(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> dict[str, Any]:
            """Below."""
            return {}

        @emits(FirstEvent)
        @regular_aspect("Below")
        async def above_aspect(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> dict[str, Any]:
            """Above."""
            return {}

        @emits(FirstEvent)
        @compensate(below_aspect, "Undo")
        async def below_compensate(
            self,
            params: _Params,
            state_before: BaseState,
            state_after: BaseState | None,
            box: ToolsBox,
            connections: Connections,
            error: Exception,
        ) -> None:
            """Above."""

        @summary_aspect("Finish")
        @emits(FirstEvent)
        async def finish_summary(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> _Result:
            """Below."""
            return _Result()

        @emits(FirstEvent)
        @on_error(ValueError, description="Handle")
        async def handle_on_error(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections, error: ValueError
        ) -> _Result:
            """Above."""
            return _Result()

    for method in (
        AnyOrderAction.order_access_decide,
        AnyOrderAction.below_aspect,
        AnyOrderAction.above_aspect,
        AnyOrderAction.below_compensate,
        AnyOrderAction.finish_summary,
        AnyOrderAction.handle_on_error,
    ):
        assert _declared(method) == (FirstEvent,)
