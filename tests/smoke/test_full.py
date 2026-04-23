# tests/smoke/test_full.py
"""
Smoke test for FullAction — full-featured action.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercises the richest action in the test domain model: two regular aspects with
checkers, a summary aspect, two dependencies (PaymentService, NotificationService),
one connection ("db"), and role "manager".

If this test passes, roles, depends, connections, checkers, the aspect pipeline, and
Result building work together.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from tests.scenarios.domain_model import FullAction


@pytest.mark.asyncio
async def test_full_action_creates_order(
    manager_bench: TestBench,
    mock_payment: AsyncMock,
    mock_notification: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """
    FullAction creates an order with correct Result fields.

    Full pipeline:
    1. "manager" role passes the check.
    2. process_payment (regular) → txn_id from PaymentService.charge().
    3. calc_total (regular) → total from params.amount.
    4. build_result (summary) → Result with order_id, txn_id, total, status.
    """
    # Arrange
    action = FullAction()
    params = FullAction.Params(user_id="user_123", amount=1500.0, currency="RUB")

    # Act
    result = await manager_bench.run(
        action, params, rollup=False, connections={"db": mock_db},
    )

    # Assert — result fields
    assert result.order_id == "ORD-user_123"
    assert result.txn_id == "TXN-TEST-001"
    assert result.total == 1500.0
    assert result.status == "created"


@pytest.mark.asyncio
async def test_full_action_calls_payment_service(
    manager_bench: TestBench,
    mock_payment: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """
    FullAction calls PaymentService.charge() with amount and currency from params.

    Ensures process_payment resolves the payment resource and passes arguments.
    """
    # Arrange
    action = FullAction()
    params = FullAction.Params(user_id="user_1", amount=999.99, currency="USD")

    # Act
    await manager_bench.run(
        action, params, rollup=False, connections={"db": mock_db},
    )

    # Assert
    mock_payment.charge.assert_called_once_with(999.99, "USD")


@pytest.mark.asyncio
async def test_full_action_calls_notification_service(
    manager_bench: TestBench,
    mock_notification: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """
    FullAction calls NotificationService.send() with user_id and message.

    Ensures build_result resolves the notification resource and sends order-created notification.
    """
    # Arrange
    action = FullAction()
    params = FullAction.Params(user_id="user_42", amount=100.0)

    # Act
    await manager_bench.run(
        action, params, rollup=False, connections={"db": mock_db},
    )

    # Assert
    mock_notification.send.assert_called_once_with(
        "user_42", "Order created: TXN-TEST-001",
    )


@pytest.mark.asyncio
async def test_full_action_result_type(
    manager_bench: TestBench,
    mock_db: AsyncMock,
) -> None:
    """
    FullAction returns an instance of FullAction.Result.

    Ensures the result is the concrete Result type, not BaseResult.
    """
    # Arrange
    action = FullAction()
    params = FullAction.Params(user_id="user_1", amount=50.0)

    # Act
    result = await manager_bench.run(
        action, params, rollup=False, connections={"db": mock_db},
    )

    # Assert
    assert isinstance(result, FullAction.Result)
