"""Extra tests for SubscriptionInfo branches."""

from __future__ import annotations

import pytest

from action_machine.intents.plugins.events import AspectEvent, BasePluginEvent, GlobalStartEvent
from action_machine.intents.plugins.subscription_info import SubscriptionInfo


class _AspectEvt(AspectEvent):
    pass


def test_subscription_info_rejects_invalid_event_class() -> None:
    with pytest.raises(TypeError):
        SubscriptionInfo(event_class=object, method_name="on_x")  # type: ignore[arg-type]


def test_subscription_info_aspect_pattern_and_regex_validation() -> None:
    with pytest.raises(ValueError):
        SubscriptionInfo(
            event_class=GlobalStartEvent,
            method_name="on_x",
            aspect_name_pattern="a.*",
        )
    with pytest.raises(ValueError):
        SubscriptionInfo(
            event_class=GlobalStartEvent,
            method_name="on_x",
            action_name_pattern="(",
        )
    with pytest.raises(ValueError):
        SubscriptionInfo(
            event_class=_AspectEvt,
            method_name="on_x",
            aspect_name_pattern="(",
        )


def test_subscription_info_filter_methods() -> None:
    sub = SubscriptionInfo(
        event_class=GlobalStartEvent,
        method_name="on_x",
        action_class=(type,),
        action_name_pattern="Action",
        nest_level=(0, 1),
        predicate=lambda e: e.nest_level == 0,
    )
    ev = GlobalStartEvent(
        action_class=BasePluginEvent,
        action_name="MyAction",
        nest_level=0,
        context=None,  # type: ignore[arg-type]
        params=None,  # type: ignore[arg-type]
    )
    assert sub.compiled_action_name_pattern is not None
    assert sub.compiled_aspect_name_pattern is None
    assert sub.matches_event_class(ev)
    assert sub.matches_action_class(type)
    assert sub.matches_action_name("MyAction")
    assert sub.matches_aspect_name(ev)
    assert sub.matches_nest_level(0)
    assert sub.matches_predicate(ev)
