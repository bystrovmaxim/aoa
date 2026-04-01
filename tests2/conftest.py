# tests2/conftest.py
"""
Общие pytest-фикстуры для всех тестов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит фикстуры, используемые во всех тестовых файлах пакета tests2/.
Фикстуры создают координатор, машины, TestBench с моками и контексты
с разными ролями. Каждый тест получает готовую инфраструктуру через
параметры фикстур — не нужно создавать машины и моки вручную.

═══════════════════════════════════════════════════════════════════════════════
СЛОИ ФИКСТУР
═══════════════════════════════════════════════════════════════════════════════

Слой 1 — Инфраструктура:
    coordinator     — GateCoordinator (новый для каждого теста).
    log_coordinator — LogCoordinator без логгеров (тихий режим для тестов).

Слой 2 — Моки зависимостей:
    mock_payment       — AsyncMock(spec=PaymentService), charge → "TXN-TEST-001".
    mock_notification  — AsyncMock(spec=NotificationService), send → True.
    mock_db            — AsyncMock(spec=TestDbManager).

Слой 3 — TestBench:
    bench         — TestBench с моками, без ролей (анонимный пользователь).
    manager_bench — TestBench с ролью "manager" (для FullAction).
    admin_bench   — TestBench с ролью "admin" (для AdminAction).

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. ИЗОЛЯЦИЯ. Каждый тест получает свежий coordinator и bench.
   Фикстуры со scope="function" (по умолчанию) гарантируют,
   что метаданные одного теста не влияют на другой.

2. ТИХИЕ ЛОГИ. LogCoordinator создаётся без логгеров — тесты
   не засоряют stdout. Для отладки можно временно добавить
   ConsoleLogger в фикстуру log_coordinator.

3. ГОТОВЫЕ BENCH. Три варианта TestBench покрывают основные
   сценарии: анонимный (bench), менеджер (manager_bench),
   админ (admin_bench). Для нестандартных ролей тест использует
   bench.with_user() напрямую.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

    async def test_ping(bench):
        # bench — готовый TestBench с моками и анонимным пользователем
        result = await bench.run(PingAction(), PingAction.Params(), rollup=False)
        assert result.message == "pong"

    async def test_full_action(manager_bench, mock_db):
        # manager_bench — TestBench с ролью "manager"
        result = await manager_bench.run(
            FullAction(),
            FullAction.Params(user_id="u1", amount=100.0),
            rollup=False,
            connections={"db": mock_db},
        )
        assert result.status == "created"

    async def test_admin_only(admin_bench):
        # admin_bench — TestBench с ролью "admin"
        result = await admin_bench.run(
            AdminAction(),
            AdminAction.Params(target="user_456"),
            rollup=False,
        )
        assert result.success is True
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.testing import TestBench

from .domain import (
    NotificationService,
    PaymentService,
    TestDbManager,
)

# ═════════════════════════════════════════════════════════════════════════════
# Слой 1 — Инфраструктура
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def coordinator() -> GateCoordinator:
    """
    Свежий GateCoordinator для каждого теста.

    Создаётся без strict-режима. Каждый тест получает чистый координатор
    без кешированных метаданных от предыдущих тестов.
    """
    return GateCoordinator()


@pytest.fixture()
def log_coordinator() -> LogCoordinator:
    """
    LogCoordinator без логгеров — тихий режим для тестов.

    Тесты не выводят сообщения в stdout. Для отладки конкретного теста
    можно временно заменить на LogCoordinator(loggers=[ConsoleLogger()]).
    """
    return LogCoordinator(loggers=[])


# ═════════════════════════════════════════════════════════════════════════════
# Слой 2 — Моки зависимостей
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def mock_payment() -> AsyncMock:
    """
    Мок PaymentService.

    charge() возвращает фиксированный txn_id "TXN-TEST-001".
    Используется в FullAction через box.resolve(PaymentService).
    """
    mock = AsyncMock(spec=PaymentService)
    mock.charge.return_value = "TXN-TEST-001"
    return mock


@pytest.fixture()
def mock_notification() -> AsyncMock:
    """
    Мок NotificationService.

    send() возвращает True (уведомление успешно отправлено).
    Используется в FullAction через box.resolve(NotificationService).
    """
    mock = AsyncMock(spec=NotificationService)
    mock.send.return_value = True
    return mock


@pytest.fixture()
def mock_db() -> AsyncMock:
    """
    Мок TestDbManager для connections.

    Передаётся в connections={"db": mock_db} при вызове FullAction.
    Не содержит настроенного поведения — тесты добавляют его при необходимости.
    """
    return AsyncMock(spec=TestDbManager)


# ═════════════════════════════════════════════════════════════════════════════
# Слой 3 — TestBench
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def bench(
    coordinator: GateCoordinator,
    log_coordinator: LogCoordinator,
    mock_payment: AsyncMock,
    mock_notification: AsyncMock,
) -> TestBench:
    """
    TestBench с моками и анонимным пользователем (ROLE_NONE).

    Подходит для тестов PingAction, SimpleAction, ChildAction —
    действий без ролевых ограничений. Для действий с ролями
    используйте manager_bench, admin_bench или bench.with_user().
    """
    return TestBench(
        coordinator=coordinator,
        log_coordinator=log_coordinator,
        mocks={
            PaymentService: mock_payment,
            NotificationService: mock_notification,
        },
    )


@pytest.fixture()
def manager_bench(bench: TestBench) -> TestBench:
    """
    TestBench с ролью "manager".

    Создаётся из bench через immutable fluent-метод with_user().
    Оригинальный bench не мутируется. Подходит для FullAction.
    """
    return bench.with_user(user_id="manager_1", roles=["manager"])


@pytest.fixture()
def admin_bench(bench: TestBench) -> TestBench:
    """
    TestBench с ролью "admin".

    Создаётся из bench через immutable fluent-метод with_user().
    Оригинальный bench не мутируется. Подходит для AdminAction.
    """
    return bench.with_user(user_id="admin_1", roles=["admin"])
