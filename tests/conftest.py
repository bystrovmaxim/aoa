# tests/conftest.py
"""
Общие фикстуры для всех тестов в пакете tests/.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Предоставляет готовые фикстуры, которые покрывают типичные потребности
тестов: координатор метаданных, моки сервисов, TestBench с различными
конфигурациями. Все фикстуры основаны на единой доменной модели
из tests/domain_model/.

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. Каждая фикстура создаёт НОВЫЙ экземпляр — тесты изолированы.
2. Моки сервисов настроены с разумными дефолтами, которые проходят
   все чекеры доменных Action.
3. TestBench фикстуры покрывают три уровня: без моков, с моками,
   с моками и ролью.

═══════════════════════════════════════════════════════════════════════════════
ЗНАЧЕНИЯ МОКОВ
═══════════════════════════════════════════════════════════════════════════════

mock_payment.charge() → "TXN-TEST-001"
    Проходит чекер result_string("txn_id", required=True, min_length=1).
    Используется в smoke-тестах и bench-тестах для проверки txn_id.

mock_payment.refund() → True
    Компенсатор вызывает refund() при откате платежа.
    Возвращает True — откат «выполнен».

mock_notification.send() → True
    Уведомление «отправлено». Smoke-тесты проверяют вызов
    send("user_42", "Order created: TXN-TEST-001").

mock_inventory.reserve() → "RES-TEST-001"
    Проходит чекер result_string("reservation_id", required=True, min_length=1).
    Используется в тестах компенсации для проверки reservation_id.

mock_inventory.unreserve() → True
    Компенсатор вызывает unreserve() при откате резервирования.
    Возвращает True — отмена «выполнена».

═══════════════════════════════════════════════════════════════════════════════
ФИКСТУРЫ
═══════════════════════════════════════════════════════════════════════════════

coordinator        — чистый GateCoordinator для каждого теста.

mock_payment       — AsyncMock(spec=PaymentService), charge → "TXN-TEST-001",
                     refund → True.
mock_notification  — AsyncMock(spec=NotificationService), send → True.
mock_inventory     — AsyncMock(spec=InventoryService), reserve → "RES-TEST-001",
                     unreserve → True.
mock_db            — AsyncMock(spec=TestDbManager).

clean_bench        — TestBench без моков, с подавленным логированием.
bench              — TestBench с моками PaymentService и NotificationService.
compensate_bench   — TestBench с моками PaymentService и InventoryService,
                     для тестов компенсации.
manager_bench      — bench с ролью "manager" (для FullAction).
admin_bench        — bench с ролью "admin" (для AdminAction).
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.core.core_action_machine import CoreActionMachine
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.testing import TestBench

from .domain_model import InventoryService, NotificationService, PaymentService, TestDbManager


@pytest.fixture
def coordinator() -> GateCoordinator:
    """Built coordinator with default inspector graph."""
    return CoreActionMachine.create_coordinator()


@pytest.fixture
def mock_payment() -> AsyncMock:
    """
    Мок PaymentService с дефолтным поведением.

    charge() возвращает "TXN-TEST-001" — проходит чекер
    result_string("txn_id", required=True, min_length=1).

    refund() возвращает True — компенсатор вызывает при откате платежа.
    Метод refund() определён в PaymentService, поэтому AsyncMock(spec=...)
    разрешает доступ к нему.
    """
    mock = AsyncMock(spec=PaymentService)
    mock.charge.return_value = "TXN-TEST-001"
    mock.refund.return_value = True
    return mock


@pytest.fixture
def mock_notification() -> AsyncMock:
    """
    Мок NotificationService с дефолтным поведением.

    send() возвращает True — уведомление «отправлено».
    """
    mock = AsyncMock(spec=NotificationService)
    mock.send.return_value = True
    return mock


@pytest.fixture
def mock_inventory() -> AsyncMock:
    """
    Мок InventoryService с дефолтным поведением.

    reserve() возвращает "RES-TEST-001" — проходит чекер
    result_string("reservation_id", required=True, min_length=1).

    unreserve() возвращает True — компенсатор вызывает при откате
    резервирования товара.
    """
    mock = AsyncMock(spec=InventoryService)
    mock.reserve.return_value = "RES-TEST-001"
    mock.unreserve.return_value = True
    return mock


@pytest.fixture
def mock_db() -> AsyncMock:
    """
    Мок TestDbManager для передачи в connections={"db": mock_db}.

    Используется в тестах FullAction, который объявляет
    @connection(TestDbManager, key="db").
    """
    return AsyncMock(spec=TestDbManager)


@pytest.fixture
def clean_bench(coordinator: GateCoordinator) -> TestBench:
    """
    TestBench без моков — для тестирования действий без зависимостей.

    Логирование подавлено через AsyncMock, чтобы не засорять
    вывод тестов сообщениями ConsoleLogger.
    """
    return TestBench(coordinator=coordinator, log_coordinator=AsyncMock())


@pytest.fixture
def bench(
    coordinator: GateCoordinator,
    mock_payment: AsyncMock,
    mock_notification: AsyncMock,
) -> TestBench:
    """
    TestBench с моками PaymentService и NotificationService.

    Дефолтный пользователь — user_id="test_user", roles=["tester"].
    Для действий с конкретными ролями используйте manager_bench
    или admin_bench.
    """
    return TestBench(
        coordinator=coordinator,
        mocks={
            PaymentService: mock_payment,
            NotificationService: mock_notification,
        },
        log_coordinator=AsyncMock(),
    )


@pytest.fixture
def compensate_bench(
    coordinator: GateCoordinator,
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
) -> TestBench:
    """
    TestBench с моками PaymentService и InventoryService.

    Предназначен для тестов компенсации (Saga). Содержит оба сервиса,
    используемых в CompensatedOrderAction, CompensateErrorAction,
    CompensateAndOnErrorAction и CompensateWithContextAction.

    Дефолтный пользователь — user_id="test_user", roles=["tester"].
    Все компенсируемые Action используют ROLE_NONE, поэтому
    дефолтный пользователь подходит.
    """
    return TestBench(
        coordinator=coordinator,
        mocks={
            PaymentService: mock_payment,
            InventoryService: mock_inventory,
        },
        log_coordinator=AsyncMock(),
    )


@pytest.fixture
def manager_bench(bench: TestBench) -> TestBench:
    """
    TestBench с ролью "manager" — для тестирования FullAction.

    FullAction требует @check_roles("manager"). Этот bench
    создаёт пользователя с ролью "manager".
    """
    return bench.with_user(user_id="mgr_1", roles=["manager"])


@pytest.fixture
def admin_bench(bench: TestBench) -> TestBench:
    """
    TestBench с ролью "admin" — для тестирования AdminAction.

    AdminAction требует @check_roles("admin"). Этот bench
    создаёт пользователя с ролью "admin".
    """
    return bench.with_user(user_id="admin_1", roles=["admin"])
