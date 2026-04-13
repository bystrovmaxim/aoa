# tests/graph/test_subscription_intent_inspector.py
"""Unit tests for SubscriptionIntentInspector."""

from __future__ import annotations

from action_machine.graph.inspectors.subscription_intent_inspector import SubscriptionIntentInspector
from action_machine.intents.plugins import GlobalFinishEvent, GlobalStartEvent, OnIntent, on


class _NoSubscriptionPlugin(OnIntent):
    pass


class _SubscriptionPlugin(OnIntent):
    @on(GlobalStartEvent)
    async def on_start(self, state, event: GlobalStartEvent, log):
        return state

    @on(GlobalFinishEvent, action_name_pattern="Order", nest_level=(0, 1))
    async def on_finish(self, state, event: GlobalFinishEvent, log):
        return state


def test_subscription_inspector_returns_none_without_subscriptions() -> None:
    assert SubscriptionIntentInspector.inspect(_NoSubscriptionPlugin) is None


def test_subscription_inspector_builds_payload_with_subscriptions() -> None:
    payload = SubscriptionIntentInspector.inspect(_SubscriptionPlugin)
    assert payload is not None
    assert payload.node_type == "subscription"

    data = dict(payload.node_meta)
    subscriptions = data["subscriptions"]
    assert len(subscriptions) == 2

    names = {entry[0] for entry in subscriptions}
    assert "on_start" in names
    assert "on_finish" in names

    finish_entry = next(entry for entry in subscriptions if entry[0] == "on_finish")
    assert finish_entry[1] is GlobalFinishEvent
    assert finish_entry[3] == "Order"
    assert finish_entry[5] == (0, 1)
