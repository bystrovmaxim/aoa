"""Extra tests for @on decorator validation branches."""

from __future__ import annotations

import pytest

from action_machine.intents.on.on_decorator import on
from action_machine.model.exceptions import NamingPrefixError
from action_machine.plugin.events import GlobalStartEvent


def test_on_rejects_bad_action_class_and_nest_level_types() -> None:
    with pytest.raises(TypeError):
        on(GlobalStartEvent, action_class=(str, 123))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        on(GlobalStartEvent, nest_level=("x",))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        on(GlobalStartEvent, nest_level=(-1,))


def test_on_rejects_non_async_and_wrong_name() -> None:
    with pytest.raises(TypeError):
        @on(GlobalStartEvent)
        def on_sync(self, state, event, log):
            return state

    with pytest.raises(NamingPrefixError):
        @on(GlobalStartEvent)
        async def handle(self, state, event, log):
            return state
