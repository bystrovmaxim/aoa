# tests/core/test_machine_connections.py
"""
Тесты валидации connections в ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ActionProductMachine._check_connections() — второй шаг конвейера после
проверки ролей. Машина сравнивает ключи, объявленные через @connection
в ClassMetadata, с фактически переданными connections и проверяет типы
значений.

Двухуровневая валидация:

1. Проверка ключей — объявленные ключи должны точно совпадать
   с фактическими.

2. Проверка типов — каждое значение должно быть экземпляром
   BaseResourceManager.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Действие без @connection:
    - Без connections (None) → пустой dict.
    - С connections → ConnectionValidationError.

Действие с одним @connection:
    - Корректный connections с совпадающим ключом → OK.
    - Без connections → ConnectionValidationError.
    - Лишний ключ → ConnectionValidationError.
    - Значение не BaseResourceManager → ConnectionValidationError.

Действие с двумя @connection:
    - Оба ключа переданы → OK.
    - Один ключ отсутствует → ConnectionValidationError.

Интеграция через run():
    - FullAction с корректными connections → результат.
    - FullAction без connections → ConnectionValidationError.
    - FullAction с лишним ключом → ConnectionValidationError.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import ConnectionValidationError
from action_machine.core.meta_decorator import meta
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import connection
from tests.domain_model import FullAction, NotificationService, PaymentService, PingAction, TestDbManager

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные действия для edge-case тестов
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Заглушка ресурсного менеджера для тестов connections")
class _MockResourceManager(BaseResourceManager):
    """Минимальная реализация BaseResourceManager для тестов."""

    def get_wrapper_class(self):
        return None


@meta(description="Действие с двумя connections")
@check_roles(ROLE_NONE)
@connection(_MockResourceManager, key="db", description="База данных")
@connection(_MockResourceManager, key="cache", description="Кеш")
class _ActionTwoConnectionsAction(BaseAction[BaseParams, BaseResult]):
    """Объявляет два подключения: db и cache."""

    @summary_aspect("test")
    async def build_summary(self, params, state, box, connections):
        return BaseResult()


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def machine() -> ActionProductMachine:
    """ActionProductMachine с тихим логгером для unit-тестов."""
    return ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )


@pytest.fixture()
def context() -> Context:
    """Контекст с ролями для прохождения проверки ролей."""
    return Context(user=UserInfo(user_id="mgr_1", roles=["manager", "admin"]))


@pytest.fixture()
def mock_resource() -> _MockResourceManager:
    """Экземпляр _MockResourceManager для передачи в connections."""
    return _MockResourceManager()


# ═════════════════════════════════════════════════════════════════════════════
# Действие без @connection
# ═════════════════════════════════════════════════════════════════════════════


class TestNoConnectionDeclaration:
    """Действие без @connection — connections не ожидаются."""

    def test_no_connections_returns_empty_dict(self, machine, context) -> None:
        """
        Действие без @connection + connections=None → пустой dict.
        """
        # Arrange — PingAction без @connection
        action = PingAction()
        metadata = machine._get_metadata(action)

        # Act — проверка с connections=None
        result = machine._check_connections(action, None, metadata)

        # Assert — пустой dict, не None
        assert result == {}

    def test_connections_provided_raises(self, machine, context, mock_resource) -> None:
        """
        Действие без @connection + connections={"db": ...} → ConnectionValidationError.
        """
        # Arrange — PingAction без @connection, но с переданным connections
        action = PingAction()
        metadata = machine._get_metadata(action)
        connections = {"db": mock_resource}

        # Act & Assert — ConnectionValidationError с указанием ключей
        with pytest.raises(ConnectionValidationError, match="does not declare any @connection"):
            machine._check_connections(action, connections, metadata)


# ═════════════════════════════════════════════════════════════════════════════
# Действие с одним @connection
# ═════════════════════════════════════════════════════════════════════════════


class TestSingleConnection:
    """Действие с одним @connection("db") — FullAction."""

    def test_correct_key_passes(self, machine, context) -> None:
        """
        FullAction + connections={"db": MockResourceManager} → OK.
        """
        # Arrange — FullAction с @connection(key="db")
        action = FullAction()
        metadata = machine._get_metadata(action)
        mock_db = AsyncMock(spec=TestDbManager)

        # Act — проверка connections
        result = machine._check_connections(action, {"db": mock_db}, metadata)

        # Assert — connections прошёл проверку, возвращён как есть
        assert "db" in result

    def test_no_connections_raises(self, machine, context) -> None:
        """
        FullAction + connections=None → ConnectionValidationError.
        """
        # Arrange — FullAction, connections=None
        action = FullAction()
        metadata = machine._get_metadata(action)

        # Act & Assert — ConnectionValidationError
        with pytest.raises(ConnectionValidationError, match="declares connections"):
            machine._check_connections(action, None, metadata)

    def test_extra_key_raises(self, machine, context, mock_resource) -> None:
        """
        FullAction + connections={"db": ..., "extra": ...} → ConnectionValidationError.
        """
        # Arrange — FullAction с лишним ключом "extra"
        action = FullAction()
        metadata = machine._get_metadata(action)
        mock_db = AsyncMock(spec=TestDbManager)
        connections = {"db": mock_db, "extra": mock_resource}

        # Act & Assert — ConnectionValidationError
        with pytest.raises(ConnectionValidationError, match="received extra connections"):
            machine._check_connections(action, connections, metadata)

    def test_value_not_resource_manager_raises(self, machine, context) -> None:
        """
        connections={"db": "строка"} → ConnectionValidationError.
        """
        # Arrange — строка вместо менеджера
        action = FullAction()
        metadata = machine._get_metadata(action)
        connections = {"db": "это строка, а не менеджер"}

        # Act & Assert — проверка типа значения
        with pytest.raises(ConnectionValidationError, match="must be an instance of BaseResourceManager"):
            machine._check_connections(action, connections, metadata)

    def test_value_none_raises(self, machine, context) -> None:
        """
        connections={"db": None} → ConnectionValidationError.
        """
        # Arrange — None вместо менеджера
        action = FullAction()
        metadata = machine._get_metadata(action)
        connections = {"db": None}

        # Act & Assert
        with pytest.raises(ConnectionValidationError, match="must be an instance of BaseResourceManager"):
            machine._check_connections(action, connections, metadata)

    def test_value_int_raises(self, machine, context) -> None:
        """
        connections={"db": 42} → ConnectionValidationError.
        """
        # Arrange — число вместо менеджера
        action = FullAction()
        metadata = machine._get_metadata(action)
        connections = {"db": 42}

        # Act & Assert
        with pytest.raises(ConnectionValidationError, match="must be an instance of BaseResourceManager"):
            machine._check_connections(action, connections, metadata)


# ═════════════════════════════════════════════════════════════════════════════
# Действие с двумя @connection
# ═════════════════════════════════════════════════════════════════════════════


class TestTwoConnections:
    """Действие с двумя @connection("db", "cache")."""

    def test_both_keys_present_passes(self, machine, context, mock_resource) -> None:
        """
        _ActionTwoConnectionsAction + connections={"db": ..., "cache": ...} → OK.
        """
        # Arrange — действие с двумя @connection, оба ключа переданы
        action = _ActionTwoConnectionsAction()
        metadata = machine._get_metadata(action)
        connections = {
            "db": _MockResourceManager(),
            "cache": _MockResourceManager(),
        }

        # Act — проверка проходит
        result = machine._check_connections(action, connections, metadata)

        # Assert — оба ключа в результате
        assert "db" in result
        assert "cache" in result

    def test_missing_key_raises(self, machine, context, mock_resource) -> None:
        """
        _ActionTwoConnectionsAction + connections={"db": ...} (без cache) →
        ConnectionValidationError.
        """
        # Arrange — только один ключ из двух объявленных
        action = _ActionTwoConnectionsAction()
        metadata = machine._get_metadata(action)
        connections = {"db": mock_resource}

        # Act & Assert — ConnectionValidationError
        with pytest.raises(ConnectionValidationError, match="missing required connections"):
            machine._check_connections(action, connections, metadata)


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция через run()
# ═════════════════════════════════════════════════════════════════════════════


class TestConnectionsViaRun:
    """Проверка connections через полный конвейер run()."""

    @pytest.mark.asyncio
    async def test_full_action_with_valid_connections(self, machine, context) -> None:
        """
        FullAction через run() с корректными connections → результат.
        """
        # Arrange — FullAction с моками зависимостей и connections
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-RUN"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=TestDbManager)

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act — run() с resources (моки) и connections
        result = await machine._run_internal(
            context=context,
            action=action,
            params=params,
            resources={PaymentService: mock_payment, NotificationService: mock_notification},
            connections={"db": mock_db},
            nested_level=0,
            rollup=False,
        )

        # Assert — конвейер завершился, результат содержит данные
        assert result.order_id == "ORD-u1"
        assert result.txn_id == "TXN-RUN"
        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_full_action_without_connections_raises(self, machine, context) -> None:
        """
        FullAction через run() без connections → ConnectionValidationError.
        """
        # Arrange — FullAction без connections
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act & Assert — ConnectionValidationError до запуска конвейера
        with pytest.raises(ConnectionValidationError):
            await machine.run(context, action, params, connections=None)

    @pytest.mark.asyncio
    async def test_full_action_with_extra_key_raises(self, machine, context) -> None:
        """
        FullAction через run() с лишним ключом → ConnectionValidationError.
        """
        # Arrange — FullAction с лишним ключом "extra"
        mock_db = AsyncMock(spec=TestDbManager)
        extra_resource = _MockResourceManager()

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)
        connections = {"db": mock_db, "extra": extra_resource}

        # Act & Assert — ConnectionValidationError с указанием лишнего ключа
        with pytest.raises(ConnectionValidationError, match="extra"):
            await machine.run(context, action, params, connections=connections)

    @pytest.mark.asyncio
    async def test_ping_action_without_connections_ok(self, machine, context) -> None:
        """
        PingAction через run() без connections → OK.
        """
        # Arrange — PingAction без @connection
        action = PingAction()
        params = PingAction.Params()

        # Act — run() без connections
        result = await machine.run(context, action, params)

        # Assert — конвейер завершился успешно
        assert result.message == "pong"
