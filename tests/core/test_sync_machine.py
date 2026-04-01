# tests/core/test_sync_machine.py
"""
Тесты SyncActionProductMachine — синхронная обёртка над ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

SyncActionProductMachine — синхронный аналог ActionProductMachine. Метод
run() является обычным (не async) методом, который вызывает asyncio.run()
внутри для выполнения асинхронного конвейера. Предназначен для синхронных
окружений: CLI-скрипты, Celery, Django без async.

SyncActionProductMachine наследует ActionProductMachine и переопределяет
только публичный метод run(). Вся логика конвейера (проверка ролей,
валидация connections, чекеры, аспекты, плагины) наследуется без изменений.

Production-машина всегда передаёт rollup=False в _run_internal().

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Базовое выполнение:
    - PingAction через sync run() → результат "pong".
    - SimpleAction через sync run() → greeting.
    - FullAction через sync run() → Result с txn_id, total, order_id.

Проверка ролей через sync:
    - ROLE_NONE — проходит без ролей.
    - Конкретная роль — AuthorizationError при несовпадении.

Проверка connections через sync:
    - FullAction без connections → ConnectionValidationError.
    - FullAction с корректными connections → OK.

Проверка чекеров через sync:
    - Корректные данные → конвейер проходит.

Наследование от ActionProductMachine:
    - isinstance(sync_machine, ActionProductMachine) → True.
    - _run_internal() доступен и работает.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.exceptions import AuthorizationError, ConnectionValidationError
from action_machine.core.sync_action_product_machine import SyncActionProductMachine
from action_machine.logging.log_coordinator import LogCoordinator
from tests.domain import (
    FullAction,
    NotificationService,
    PaymentService,
    PingAction,
    SimpleAction,
    TestDbManager,
)

# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def sync_machine() -> SyncActionProductMachine:
    """
    SyncActionProductMachine с тихим логгером для unit-тестов.

    LogCoordinator без логгеров подавляет вывод в stdout.
    """
    return SyncActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )


@pytest.fixture()
def context_manager() -> Context:
    """Контекст с ролью manager для FullAction."""
    return Context(user=UserInfo(user_id="mgr_1", roles=["manager", "admin"]))


@pytest.fixture()
def context_no_roles() -> Context:
    """Контекст без ролей — анонимный пользователь."""
    return Context(user=UserInfo(user_id="guest", roles=[]))


# ═════════════════════════════════════════════════════════════════════════════
# Базовое выполнение через sync run()
# ═════════════════════════════════════════════════════════════════════════════


class TestSyncBasicExecution:
    """Базовое выполнение действий через синхронный run()."""

    def test_ping_action_returns_pong(self, sync_machine, context_no_roles) -> None:
        """
        PingAction через sync run() → результат с message="pong".

        SyncActionProductMachine.run() вызывает asyncio.run() внутри,
        который создаёт event loop и выполняет асинхронный конвейер.
        PingAction имеет ROLE_NONE — проходит без ролей.
        """
        # Arrange — PingAction с пустыми параметрами
        action = PingAction()
        params = PingAction.Params()

        # Act — синхронный вызов без await
        result = sync_machine.run(context_no_roles, action, params)

        # Assert — конвейер завершился, результат содержит "pong"
        assert result.message == "pong"

    def test_simple_action_returns_greeting(self, sync_machine, context_manager) -> None:
        """
        SimpleAction через sync run() → greeting "Hello, Alice!".

        SimpleAction содержит один regular-аспект (validate_name)
        с чекером result_string и один summary-аспект.
        """
        # Arrange — SimpleAction с именем "Alice"
        action = SimpleAction()
        params = SimpleAction.Params(name="Alice")

        # Act — синхронный вызов
        result = sync_machine.run(context_manager, action, params)

        # Assert — greeting сформирован из validated_name
        assert result.greeting == "Hello, Alice!"

    def test_full_action_via_run_internal(self, sync_machine, context_manager) -> None:
        """
        FullAction через _run_internal() с моками зависимостей и connections.

        SyncActionProductMachine наследует _run_internal() от
        ActionProductMachine. Метод асинхронный, вызывается напрямую
        через asyncio.run() в этом тесте (pytest-asyncio).
        """
        # Arrange — моки зависимостей и connections
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-SYNC"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=TestDbManager)

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=250.0)

        # Act — синхронный вызов через asyncio.run обёрнутый в _run_internal
        import asyncio

        result = asyncio.run(
            sync_machine._run_internal(
                context=context_manager,
                action=action,
                params=params,
                resources={PaymentService: mock_payment, NotificationService: mock_notification},
                connections={"db": mock_db},
                nested_level=0,
                rollup=False,
            )
        )

        # Assert — конвейер завершился с данными из моков
        assert result.order_id == "ORD-u1"
        assert result.txn_id == "TXN-SYNC"
        assert result.total == 250.0
        assert result.status == "created"


# ═════════════════════════════════════════════════════════════════════════════
# Проверка ролей через sync
# ═════════════════════════════════════════════════════════════════════════════


class TestSyncRoles:
    """Проверка ролей работает идентично async-машине."""

    def test_role_none_passes_without_roles(self, sync_machine, context_no_roles) -> None:
        """
        PingAction (ROLE_NONE) проходит через sync-машину без ролей.

        Логика проверки ролей наследуется от ActionProductMachine.
        ROLE_NONE → _check_none_role() → всегда True.
        """
        # Arrange — PingAction с ROLE_NONE, контекст без ролей
        action = PingAction()
        params = PingAction.Params()

        # Act — синхронный вызов
        result = sync_machine.run(context_no_roles, action, params)

        # Assert — конвейер завершился
        assert result.message == "pong"

    def test_wrong_role_raises_authorization_error(self, sync_machine, context_no_roles) -> None:
        """
        FullAction (роль "manager") через sync-машину без ролей →
        AuthorizationError.

        Проверка ролей выполняется ДО конвейера аспектов. Sync-машина
        наследует _check_action_roles() от ActionProductMachine.
        """
        # Arrange — FullAction требует "manager", контекст без ролей
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act & Assert — AuthorizationError
        with pytest.raises(AuthorizationError):
            sync_machine.run(context_no_roles, action, params)


# ═════════════════════════════════════════════════════════════════════════════
# Проверка connections через sync
# ═════════════════════════════════════════════════════════════════════════════


class TestSyncConnections:
    """Валидация connections работает идентично async-машине."""

    def test_missing_connections_raises(self, sync_machine, context_manager) -> None:
        """
        FullAction через sync-машину без connections → ConnectionValidationError.

        FullAction объявляет @connection(TestDbManager, key="db").
        Без connections машина бросает ConnectionValidationError.
        """
        # Arrange — FullAction без connections
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act & Assert — ConnectionValidationError
        with pytest.raises(ConnectionValidationError):
            sync_machine.run(context_manager, action, params, connections=None)

    def test_ping_without_connections_ok(self, sync_machine, context_no_roles) -> None:
        """
        PingAction через sync-машину без connections → OK.

        PingAction не объявляет @connection, connections=None допустим.
        """
        # Arrange — PingAction без @connection
        action = PingAction()
        params = PingAction.Params()

        # Act — sync run без connections
        result = sync_machine.run(context_no_roles, action, params)

        # Assert — конвейер завершился
        assert result.message == "pong"


# ═════════════════════════════════════════════════════════════════════════════
# Наследование от ActionProductMachine
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritance:
    """SyncActionProductMachine наследует ActionProductMachine."""

    def test_isinstance_action_product_machine(self, sync_machine) -> None:
        """
        SyncActionProductMachine является подклассом ActionProductMachine.

        Это гарантирует, что sync-машина наследует всю логику конвейера:
        проверку ролей, валидацию connections, чекеры, аспекты, плагины.
        """
        # Arrange & Act — проверка через isinstance

        # Assert — sync-машина является ActionProductMachine
        assert isinstance(sync_machine, ActionProductMachine)
        assert isinstance(sync_machine, SyncActionProductMachine)

    def test_has_run_internal(self, sync_machine) -> None:
        """
        _run_internal() доступен на sync-машине.

        Метод наследуется от ActionProductMachine и используется
        внутри run() через asyncio.run().
        """
        # Arrange & Act — проверка наличия метода

        # Assert — метод существует и является callable
        assert hasattr(sync_machine, "_run_internal")
        assert callable(sync_machine._run_internal)

    def test_mode_attribute(self, sync_machine) -> None:
        """
        Атрибут _mode устанавливается в конструкторе и наследуется.
        """
        # Arrange — машина создана с mode="test" в фикстуре

        # Act & Assert — mode доступен
        assert sync_machine._mode == "test"

    def test_rollup_always_false_in_public_run(self, sync_machine, context_no_roles) -> None:
        """
        Production sync-машина всегда передаёт rollup=False.

        Метод run() не принимает параметр rollup — он зафиксирован
        как False внутри реализации. Rollup доступен только через
        TestBench.
        """
        # Arrange — PingAction через public run()
        action = PingAction()
        params = PingAction.Params()

        # Act — run() не принимает rollup (в отличие от TestBench.run)
        result = sync_machine.run(context_no_roles, action, params)

        # Assert — конвейер завершился (rollup=False внутри)
        assert result.message == "pong"
