# tests/runtime/test_machine_plugins_events_count.py
"""Plugin ``emit_event`` call counts: formula 4 + 2*N regular aspects."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.runtime.action_product_machine import ActionProductMachine
from tests.scenarios.domain_model import FullAction, OrdersDbManager, PingAction, SimpleAction
from tests.scenarios.domain_model.services import (
    NotificationService,
    NotificationServiceResource,
    PaymentService,
    PaymentServiceResource,
)


class TestEventCount:
    """``emit_event`` count depends on the number of regular aspects (4 + 2*N)."""

    @pytest.mark.asyncio
    async def test_ping_action_emits_four_events(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = PingAction()
        params = PingAction.Params()
        await machine_with_mock_plugins.run(context, action, params)
        assert mock_plugin_ctx.emit_event.await_count == 4

    @pytest.mark.asyncio
    async def test_simple_action_emits_six_events(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        action = SimpleAction()
        params = SimpleAction.Params(name="Alice")
        await machine_with_mock_plugins.run(context, action, params)
        assert mock_plugin_ctx.emit_event.await_count == 6

    @pytest.mark.asyncio
    async def test_full_action_emits_eight_events(
        self,
        machine_with_mock_plugins: ActionProductMachine,
        mock_plugin_ctx: AsyncMock,
        context: Context,
    ) -> None:
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-EVT"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=OrdersDbManager)

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        await machine_with_mock_plugins._run_internal(
            context=context,
            action=action,
            params=params,
            resources={
                PaymentServiceResource: PaymentServiceResource(mock_payment),
                NotificationServiceResource: NotificationServiceResource(mock_notification),
            },
            connections={"db": mock_db},
            nested_level=0,
            rollup=False,
        )

        assert mock_plugin_ctx.emit_event.await_count == 8
