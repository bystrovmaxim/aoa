# tests/intents/plugins/test_on_intent_validators.py
"""OnIntent marker and subscription vs handler annotation checks."""

from types import SimpleNamespace

import pytest

from action_machine.intents.plugins.events import GlobalStartEvent, UnhandledErrorEvent
from action_machine.intents.plugins.on_intent import OnIntent, require_on_intent_marker, validate_subscriptions
from action_machine.intents.plugins.subscription_info import SubscriptionInfo


def test_require_on_intent_marker_raises_without_mixin() -> None:
    class Plain:
        pass

    subs = [SimpleNamespace()]
    with pytest.raises(TypeError, match="OnIntent"):
        require_on_intent_marker(Plain, subs)


def test_require_on_intent_marker_lists_subscription_info_event_classes() -> None:
    class Plain:
        pass

    sub = SubscriptionInfo(event_class=GlobalStartEvent, method_name="m")
    with pytest.raises(TypeError, match="GlobalStartEvent"):
        require_on_intent_marker(Plain, [sub])


def test_validate_subscriptions_rejects_event_class_mismatch_with_annotation() -> None:
    class _Plugin:
        async def hook(self, _state, event: GlobalStartEvent, _log) -> None:
            del event

    sub = SubscriptionInfo(event_class=UnhandledErrorEvent, method_name="hook")
    with pytest.raises(TypeError, match="UnhandledErrorEvent"):
        validate_subscriptions(_Plugin, [sub])


def test_validate_subscriptions_skips_non_subscription_entries() -> None:
    class _Plugin(OnIntent):
        async def hook(self, _state, event: GlobalStartEvent, _log) -> None:
            del event

    validate_subscriptions(_Plugin, [SimpleNamespace()])
