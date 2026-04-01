# tests/conftest.py
"""
Общие фикстуры для всех тестов в пакете tests/.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Предоставляет готовые фикстуры, которые покрывают типичные потребности
тестов: координатор метаданных, моки сервисов, TestBench с различными
конфигурациями. Все фикстуры основаны на единой доменной модели
из tests/domain/.

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

mock_notification.send() → True
    Уведомление «отправлено». Smoke-тесты проверяют вызов
    send("user_42", "Заказ создан: TXN-TEST-001").

═══════════════════════════════════════════════════════════════════════════════
ФИКСТУРЫ
═══════════════════════════════════════════════════════════════════════════════

coordinator        — чистый GateCoordinator для каждого теста.
mock_payment       — AsyncMock(spec=PaymentService), charge → "TXN-TEST-001".
mock_notification  — AsyncMock(spec=NotificationService), send → True.
mock_db            — AsyncMock(spec=TestDbManager).
clean_bench        — TestBench без моков, с подавленным логированием.
bench              — TestBench с моками PaymentService и NotificationService.
manager_bench      — bench с ролью "manager" (для FullAction).
admin_bench        — bench с ролью "admin" (для AdminAction).
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.testing import TestBench

from .domain import NotificationService, PaymentService, TestDbManager


@pytest.fixture
def coordinator() -> GateCoordinator:
    """Чистый координатор метаданных — без кеша, без графа."""
    return GateCoordinator()


@pytest.fixture
def mock_payment() -> AsyncMock:
    """
    Мок PaymentService с дефолтным поведением.

    charge() возвращает "TXN-TEST-001" — проходит чекер
    result_string("txn_id", required=True, min_length=1).
    """
    mock = AsyncMock(spec=PaymentService)
    mock.charge.return_value = "TXN-TEST-001"
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
def mock_db() -> AsyncMock:
    """
    Мок TestDbManager для передачи в connections={"db": mock_db}.

    Используется в тестах FullAction, который объявляет
    @connection(TestDbManager, key="db").
    """
    return AsyncMock(spec=TestDbManager)


@pytest.fixture
def clean_bench() -> TestBench:
    """
    TestBench без моков — для тестирования действий без зависимостей.

    Логирование подавлено через AsyncMock, чтобы не засорять
    вывод тестов сообщениями ConsoleLogger.
    """
    return TestBench(log_coordinator=AsyncMock())


@pytest.fixture
def bench(mock_payment: AsyncMock, mock_notification: AsyncMock) -> TestBench:
    """
    TestBench с моками PaymentService и NotificationService.

    Дефолтный пользователь — user_id="test_user", roles=["tester"].
    Для действий с конкретными ролями используйте manager_bench
    или admin_bench.
    """
    return TestBench(
        mocks={
            PaymentService: mock_payment,
            NotificationService: mock_notification,
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
