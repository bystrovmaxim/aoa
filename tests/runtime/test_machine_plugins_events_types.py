# tests/runtime/test_machine_plugins_events_types.py
"""Plugin event types and ordering (typed ``BasePluginEvent`` hierarchy)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.plugin.events import (
    AfterSummaryAspectEvent,
    BeforeSummaryAspectEvent,
    GlobalFinishEvent,
    GlobalStartEvent,
)
from action_machine.runtime.action_product_machine import ActionProductMachine
from tests.runtime._machine_plugins_helpers import extract_event_types
from tests.scenarios.domain_model import (
    FullAction,
    NotificationService,
    PaymentService,
    PingAction,
    SimpleAction,
    TestDbManager,
)


class TestEventTypes:
    """Event types and order."""

    @pytest.mark.asyncio
    async def test_ping_event_types(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = PingAction()
        params = PingAction.Params()
        await machine_with_mock_plugins.run(context, action, params)
        event_types = extract_event_types(mock_plugin_ctx)
        assert event_types[0] == "GlobalStartEvent"
        assert event_types[-1] == "GlobalFinishEvent"

    @pytest.mark.asyncio
    async def test_simple_action_event_order(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = SimpleAction()
        params = SimpleAction.Params(name="Bob")
        await machine_with_mock_plugins.run(context, action, params)
        event_types = extract_event_types(mock_plugin_ctx)
        assert event_types == [
            "GlobalStartEvent",
            "BeforeRegularAspectEvent",
            "AfterRegularAspectEvent",
            "BeforeSummaryAspectEvent",
            "AfterSummaryAspectEvent",
            "GlobalFinishEvent",
        ]

    @pytest.mark.asyncio
    async def test_full_action_event_order(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-ORD"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=TestDbManager)

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=200.0)

        await machine_with_mock_plugins._run_internal(
            context=context,
            action=action,
            params=params,
            resources={PaymentService: mock_payment, NotificationService: mock_notification},
            connections={"db": mock_db},
            nested_level=0,
            rollup=False,
        )

        event_types = extract_event_types(mock_plugin_ctx)
        assert event_types == [
            "GlobalStartEvent",
            "BeforeRegularAspectEvent",
            "AfterRegularAspectEvent",
            "BeforeRegularAspectEvent",
            "AfterRegularAspectEvent",
            "BeforeSummaryAspectEvent",
            "AfterSummaryAspectEvent",
            "GlobalFinishEvent",
        ]

    @pytest.mark.asyncio
    async def test_events_are_correct_isinstance(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = PingAction()
        params = PingAction.Params()
        await machine_with_mock_plugins.run(context, action, params)
        calls = mock_plugin_ctx.emit_event.call_args_list
        assert isinstance(calls[0].args[0], GlobalStartEvent)
        assert isinstance(calls[1].args[0], BeforeSummaryAspectEvent)
        assert isinstance(calls[2].args[0], AfterSummaryAspectEvent)
        assert isinstance(calls[3].args[0], GlobalFinishEvent)
