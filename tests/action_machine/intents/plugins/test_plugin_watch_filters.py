# tests/action_machine/intents/plugins/test_plugin_watch_filters.py
"""Unit tests for Plugin.get_handlers() watch_actions and watch_events filters."""

from __future__ import annotations

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.intents.on.on_decorator import on
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.plugin.core.events import GlobalFinishEvent, GlobalStartEvent
from aoa.action_machine.plugin.core.plugin import Plugin
from tests.action_machine.scenarios.domain_model import PingAction

_CTX = Context(user=UserInfo(user_id="u1", roles=()))
_PARAMS = BaseParams()


class _AnotherAction:
    """Stub action class distinct from PingAction."""


class _BaseParentAction:
    """Stub base for subclass filter test."""


class _ChildAction(_BaseParentAction):
    """Subclass of _BaseParentAction."""


def _make_start_event(action_class: type = PingAction) -> GlobalStartEvent:
    return GlobalStartEvent(
        action_class=action_class,
        action_name=action_class.__name__,
        nest_level=1,
        context=_CTX,
        params=_PARAMS,
    )


def _make_finish_event(action_class: type = PingAction) -> GlobalFinishEvent:
    result = PingAction.Result(message="pong")
    return GlobalFinishEvent(
        action_class=action_class,
        action_name=action_class.__name__,
        nest_level=1,
        context=_CTX,
        params=_PARAMS,
        result=result,
        duration_ms=1.0,
    )


class _AllEventsPlugin(Plugin):
    """Plugin subscribed to all events."""

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalStartEvent)
    async def on_start(self, state, event, log):
        return state

    @on(GlobalFinishEvent)
    async def on_finish(self, state, event, log):
        return state


# ═════════════════════════════════════════════════════════════════════════════
# watch_actions filter
# ═════════════════════════════════════════════════════════════════════════════


class TestWatchActionsFilter:
    """watch_actions filters by issubclass on event.action_class."""

    def test_no_filter_passes_all(self) -> None:
        plugin = _AllEventsPlugin()
        event = _make_start_event(action_class=PingAction)
        assert len(plugin.get_handlers(event)) > 0

    def test_matching_action_passes(self) -> None:
        plugin = _AllEventsPlugin(watch_actions=frozenset({PingAction}))
        event = _make_start_event(action_class=PingAction)
        assert len(plugin.get_handlers(event)) > 0

    def test_non_matching_action_blocked(self) -> None:
        plugin = _AllEventsPlugin(watch_actions=frozenset({PingAction}))
        event = _make_start_event(action_class=_AnotherAction)
        assert plugin.get_handlers(event) == []

    def test_subclass_action_passes_with_base_filter(self) -> None:
        plugin = _AllEventsPlugin(watch_actions=frozenset({_BaseParentAction}))
        event = _make_start_event(action_class=_ChildAction)
        assert len(plugin.get_handlers(event)) > 0

    def test_parent_blocked_when_only_subclass_in_filter(self) -> None:
        plugin = _AllEventsPlugin(watch_actions=frozenset({_ChildAction}))
        event = _make_start_event(action_class=_BaseParentAction)
        assert plugin.get_handlers(event) == []


# ═════════════════════════════════════════════════════════════════════════════
# watch_events filter
# ═════════════════════════════════════════════════════════════════════════════


class TestWatchEventsFilter:
    """watch_events filters by isinstance on the event object."""

    def test_no_filter_passes_all_event_types(self) -> None:
        plugin = _AllEventsPlugin()
        assert len(plugin.get_handlers(_make_start_event())) > 0
        assert len(plugin.get_handlers(_make_finish_event())) > 0

    def test_matching_event_type_passes(self) -> None:
        plugin = _AllEventsPlugin(watch_events=frozenset({GlobalStartEvent}))
        assert len(plugin.get_handlers(_make_start_event())) > 0

    def test_non_matching_event_type_blocked(self) -> None:
        plugin = _AllEventsPlugin(watch_events=frozenset({GlobalFinishEvent}))
        assert plugin.get_handlers(_make_start_event()) == []

    def test_finish_event_passes_with_finish_filter(self) -> None:
        plugin = _AllEventsPlugin(watch_events=frozenset({GlobalFinishEvent}))
        assert len(plugin.get_handlers(_make_finish_event())) > 0

    def test_start_blocked_when_only_finish_watched(self) -> None:
        plugin = _AllEventsPlugin(watch_events=frozenset({GlobalFinishEvent}))
        assert plugin.get_handlers(_make_start_event()) == []


# ═════════════════════════════════════════════════════════════════════════════
# Both filters — AND logic
# ═════════════════════════════════════════════════════════════════════════════


class TestBothFiltersAndLogic:
    """Both filters must pass; failing either blocks all handlers."""

    def test_both_match_passes(self) -> None:
        plugin = _AllEventsPlugin(
            watch_actions=frozenset({PingAction}),
            watch_events=frozenset({GlobalStartEvent}),
        )
        event = _make_start_event(action_class=PingAction)
        assert len(plugin.get_handlers(event)) > 0

    def test_action_mismatch_blocks_even_if_event_matches(self) -> None:
        plugin = _AllEventsPlugin(
            watch_actions=frozenset({PingAction}),
            watch_events=frozenset({GlobalStartEvent}),
        )
        event = _make_start_event(action_class=_AnotherAction)
        assert plugin.get_handlers(event) == []

    def test_event_mismatch_blocks_even_if_action_matches(self) -> None:
        plugin = _AllEventsPlugin(
            watch_actions=frozenset({PingAction}),
            watch_events=frozenset({GlobalFinishEvent}),
        )
        event = _make_start_event(action_class=PingAction)
        assert plugin.get_handlers(event) == []
