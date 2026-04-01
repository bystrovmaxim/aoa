# tests2/smoke/test_full.py
"""
Smoke-тест FullAction — полнофункциональное действие.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет самое сложное действие тестовой доменной модели: два
regular-аспекта с чекерами, summary-аспект, две зависимости
(PaymentService, NotificationService), одно connection ("db")
и ролевое ограничение "manager".

Если этот тест зелёный — все механизмы работают вместе: роли,
depends, connections, чекеры, конвейер аспектов, формирование Result.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from tests2.domain import FullAction


@pytest.mark.asyncio
async def test_full_action_creates_order(
    manager_bench: TestBench,
    mock_payment: AsyncMock,
    mock_notification: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """
    FullAction создаёт заказ с корректными полями Result.

    Проверяет полный конвейер:
    1. Роль "manager" проходит проверку.
    2. process_payment (regular) → txn_id из PaymentService.charge().
    3. calc_total (regular) → total из params.amount.
    4. build_result (summary) → Result с order_id, txn_id, total, status.
    """
    # Arrange
    action = FullAction()
    params = FullAction.Params(user_id="user_123", amount=1500.0, currency="RUB")

    # Act
    result = await manager_bench.run(
        action, params, rollup=False, connections={"db": mock_db},
    )

    # Assert — поля результата
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
    FullAction вызывает PaymentService.charge() с суммой и валютой из params.

    Проверяет, что аспект process_payment корректно резолвит
    PaymentService через box.resolve() и передаёт аргументы.
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
    FullAction вызывает NotificationService.send() с user_id и сообщением.

    Проверяет, что summary-аспект build_result резолвит
    NotificationService и отправляет уведомление о создании заказа.
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
        "user_42", "Заказ создан: TXN-TEST-001",
    )


@pytest.mark.asyncio
async def test_full_action_result_type(
    manager_bench: TestBench,
    mock_db: AsyncMock,
) -> None:
    """
    FullAction возвращает экземпляр FullAction.Result.

    Проверяет, что результат — конкретный тип Result, а не BaseResult.
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
