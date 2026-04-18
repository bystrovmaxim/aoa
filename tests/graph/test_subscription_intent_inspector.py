# tests/graph/test_subscription_intent_inspector.py
"""Unit tests for SubscriptionIntentInspector."""

from __future__ import annotations

from action_machine.graph.inspectors.subscription_intent_inspector import SubscriptionIntentInspector
from action_machine.intents.plugins import GlobalFinishEvent, GlobalStartEvent, OnIntent, on
from maxitor.samples.store.plugins.unhandled_error_plugin import UnhandledErrorSwallowPlugin


class _NoSubscriptionPlugin(OnIntent):
    pass


class _SubscriptionPlugin(OnIntent):
    @on(GlobalStartEvent)
    async def on_start(self, state, event: GlobalStartEvent, log):
        return state

    @on(GlobalFinishEvent, action_name_pattern="Order", nest_level=(0, 1))
    async def on_finish(self, state, event: GlobalFinishEvent, log):
        return state


def test_subscription_inspector_never_emits_graph_facets() -> None:
    for target in (_NoSubscriptionPlugin, _SubscriptionPlugin, UnhandledErrorSwallowPlugin):
        assert SubscriptionIntentInspector.inspect(target) is None
        assert SubscriptionIntentInspector.facet_snapshot_for_class(target) is None


def test_subscription_inspector_build_payload_for_abc_contract() -> None:
    """``_build_payload`` remains the single projection path if tooling calls it."""
    payload = SubscriptionIntentInspector._build_payload(_SubscriptionPlugin)
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
