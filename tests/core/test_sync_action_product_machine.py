# tests/core/test_sync_action_product_machine.py
"""
Тесты для SyncActionProductMachine — синхронной production-машины.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Конструктор:
    - Принимает те же параметры что ActionProductMachine (mode, coordinator, plugins).
    - Пустой mode — ValueError.

run() — синхронный вызов:
    - Простое действие выполняется и возвращает результат.
    - Действие с несколькими аспектами — порядок выполнения сохраняется.
    - Проверка ролей работает — ROLE_NONE пропускает, "admin" отклоняет tester.
    - Проверка соединений работает — отсутствие объявленного соединения отклоняется.
    - Чекеры работают — лишние поля в результате аспекта отклоняются.

Совместимость с ActionProductMachine:
    - Одно и то же действие даёт одинаковый результат на async и sync машинах.
    - Метаданные из одного coordinator доступны обеим машинам.
"""

from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_string
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import AuthorizationError, ConnectionValidationError, ValidationFieldError
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.core.sync_action_product_machine import SyncActionProductMachine
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import connection

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели и действия
# ═════════════════════════════════════════════════════════════════════════════


class SimpleParams(BaseParams):
    """Пустые параметры."""
    pass


class SimpleResult(BaseResult):
    """Пустой результат."""
    pass


class OrderParams(BaseParams):
    """Параметры заказа."""
    user_id: str = Field(description="ID пользователя", min_length=1)


class OrderResult(BaseResult):
    """Результат заказа."""
    order_id: str = Field(default="", description="ID заказа")


@meta(description="Пинг")
@check_roles(ROLE_NONE)
class PingAction(BaseAction[SimpleParams, SimpleResult]):
    """Простейшее действие — один summary."""

    @summary_aspect("pong")
    async def pong(self, params, state, box, connections):
        """Фиксированный ответ."""
        result = SimpleResult()
        result["message"] = "pong"
        return result


@meta(description="Действие с двумя аспектами")
@check_roles(ROLE_NONE)
class TwoAspectAction(BaseAction[OrderParams, OrderResult]):
    """validate → validated_user, summary → OrderResult."""

    execution_order: list[str] = []

    @regular_aspect("Валидация")
    @result_string("validated_user", required=True)
    async def validate(self, params, state, box, connections):
        """Записывает validated_user."""
        TwoAspectAction.execution_order.append("validate")
        return {"validated_user": params.user_id}

    @summary_aspect("Результат")
    async def build_result(self, params, state, box, connections):
        """Собирает OrderResult."""
        TwoAspectAction.execution_order.append("summary")
        return OrderResult(order_id=f"ORD-{state['validated_user']}")


@meta(description="Только для админов")
@check_roles("admin")
class AdminAction(BaseAction[SimpleParams, SimpleResult]):
    """Требует роль admin."""

    @summary_aspect("admin")
    async def summary(self, params, state, box, connections):
        """Доступно только админам."""
        return SimpleResult()


@meta(description="Заглушка ресурсного менеджера")
class MockResourceManager(BaseResourceManager):
    """Заглушка для тестов соединений."""
    def get_wrapper_class(self):
        return None


@connection(MockResourceManager, key="db", description="БД")
@meta(description="Действие с соединением")
@check_roles(ROLE_NONE)
class ActionWithConnection(BaseAction[SimpleParams, SimpleResult]):
    """Требует соединение db."""

    @summary_aspect("test")
    async def summary(self, params, state, box, connections):
        """Проверяет наличие db в connections."""
        assert "db" in connections
        return SimpleResult()


@meta(description="Действие с лишним полем в аспекте")
@check_roles(ROLE_NONE)
class BadCheckerAction(BaseAction[SimpleParams, SimpleResult]):
    """Аспект с чекером на одно поле, но возвращает лишнее."""

    @regular_aspect("bad")
    @result_string("name", required=True)
    async def bad_aspect(self, params, state, box, connections):
        """Возвращает лишнее поле extra."""
        return {"name": "ok", "extra": "forbidden"}

    @summary_aspect("summary")
    async def summary(self, params, state, box, connections):
        """Собирает результат."""
        return SimpleResult()


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def coordinator() -> GateCoordinator:
    return GateCoordinator()


@pytest.fixture
def sync_machine(coordinator) -> SyncActionProductMachine:
    return SyncActionProductMachine(
        mode="test",
        coordinator=coordinator,
        log_coordinator=AsyncMock(),
    )


@pytest.fixture
def async_machine(coordinator) -> ActionProductMachine:
    return ActionProductMachine(
        mode="test",
        coordinator=coordinator,
        log_coordinator=AsyncMock(),
    )


@pytest.fixture
def context() -> Context:
    return Context(user=UserInfo(user_id="tester", roles=["tester"]))


@pytest.fixture
def admin_context() -> Context:
    return Context(user=UserInfo(user_id="admin", roles=["admin"]))


# ═════════════════════════════════════════════════════════════════════════════
# Конструктор
# ═════════════════════════════════════════════════════════════════════════════


class TestConstructor:

    def test_empty_mode_raises(self):
        """Пустой mode — ValueError, как и у ActionProductMachine."""
        with pytest.raises(ValueError, match="mode must be non-empty"):
            SyncActionProductMachine(mode="")

    def test_default_coordinator(self):
        """Без coordinator — создаётся GateCoordinator по умолчанию."""
        machine = SyncActionProductMachine(mode="test")
        assert machine._coordinator is not None

    def test_default_log_coordinator(self):
        """Без log_coordinator — создаётся дефолтный с ConsoleLogger."""
        machine = SyncActionProductMachine(mode="test")
        assert machine._log_coordinator is not None


# ═════════════════════════════════════════════════════════════════════════════
# run() — синхронный вызов
# ═════════════════════════════════════════════════════════════════════════════


class TestRun:

    def test_simple_action(self, sync_machine, context):
        """
        Проверяет, что синхронный run() выполняет действие и возвращает результат:

        PingAction не имеет зависимостей. sync_machine.run() вызывает asyncio.run()
        внутри и возвращает SimpleResult синхронно.
        """
        result = sync_machine.run(context, PingAction(), SimpleParams())
        assert isinstance(result, SimpleResult)
        assert result["message"] == "pong"

    def test_aspect_execution_order(self, sync_machine, context):
        """
        Проверяет, что порядок выполнения аспектов сохраняется:

        TwoAspectAction: validate → summary. Порядок записывается
        в execution_order. Синхронная машина не должна менять порядок.
        """
        TwoAspectAction.execution_order = []
        sync_machine.run(context, TwoAspectAction(), OrderParams(user_id="u1"))
        assert TwoAspectAction.execution_order == ["validate", "summary"]

    def test_aspect_result_in_summary(self, sync_machine, context):
        """
        Проверяет, что state от regular-аспекта доступен в summary:

        validate записывает validated_user="u1". summary читает его
        и формирует order_id="ORD-u1".
        """
        result = sync_machine.run(context, TwoAspectAction(), OrderParams(user_id="u1"))
        assert result.order_id == "ORD-u1"

    def test_role_none_allows_any_user(self, sync_machine, context):
        """ROLE_NONE — действие доступно любому пользователю, включая tester."""
        result = sync_machine.run(context, PingAction(), SimpleParams())
        assert isinstance(result, SimpleResult)

    def test_admin_role_rejects_tester(self, sync_machine, context):
        """
        Проверяет, что ролевая проверка работает в синхронной машине:

        AdminAction требует "admin". Контекст содержит roles=["tester"].
        Синхронная машина должна бросить AuthorizationError.
        """
        with pytest.raises(AuthorizationError):
            sync_machine.run(context, AdminAction(), SimpleParams())

    def test_admin_role_allows_admin(self, sync_machine, admin_context):
        """AdminAction с admin-контекстом — проходит."""
        result = sync_machine.run(admin_context, AdminAction(), SimpleParams())
        assert isinstance(result, SimpleResult)

    def test_missing_connection_raises(self, sync_machine, context):
        """
        Проверяет, что проверка соединений работает в синхронной машине:

        ActionWithConnection требует db. Вызов без connections — ошибка.
        """
        with pytest.raises(ConnectionValidationError):
            sync_machine.run(context, ActionWithConnection(), SimpleParams())

    def test_valid_connection_passes(self, sync_machine, context):
        """ActionWithConnection с db=MockResourceManager() — проходит."""
        conns = {"db": MockResourceManager()}
        result = sync_machine.run(context, ActionWithConnection(), SimpleParams(), connections=conns)
        assert isinstance(result, SimpleResult)

    def test_extra_fields_in_aspect_rejected(self, sync_machine, context):
        """
        Проверяет, что чекеры работают в синхронной машине:

        BadCheckerAction возвращает лишнее поле extra — ValidationFieldError.
        """
        with pytest.raises(ValidationFieldError, match="extra"):
            sync_machine.run(context, BadCheckerAction(), SimpleParams())


# ═════════════════════════════════════════════════════════════════════════════
# Совместимость с ActionProductMachine
# ═════════════════════════════════════════════════════════════════════════════


class TestCompatibility:

    @pytest.mark.anyio
    def test_same_result_as_async(self, sync_machine, async_machine, context):
        """
        Проверяет, что sync и async машины дают одинаковый результат.

        Тест синхронный — sync_machine.run() вызывает asyncio.run() внутри.
        async_machine проверяется отдельно через asyncio.run().
        """
        import asyncio

        TwoAspectAction.execution_order = []
        async_result = asyncio.run(
            async_machine.run(context, TwoAspectAction(), OrderParams(user_id="u1"))
        )

        TwoAspectAction.execution_order = []
        sync_result = sync_machine.run(
            context, TwoAspectAction(), OrderParams(user_id="u1"),
        )

        assert async_result.order_id == sync_result.order_id
        assert async_result.order_id == "ORD-u1"

    def test_shared_coordinator(self, coordinator, context):
        """
        Проверяет, что sync и async машины используют один coordinator:

        Метаданные, собранные при первом обращении через одну машину,
        доступны другой машине из того же coordinator без повторной сборки.
        """
        sync_m = SyncActionProductMachine(
            mode="test", coordinator=coordinator, log_coordinator=AsyncMock(),
        )

        sync_m.run(context, PingAction(), SimpleParams())
        assert coordinator.has(PingAction)

        meta = coordinator.get(PingAction)
        assert meta.meta.description == "Пинг"
