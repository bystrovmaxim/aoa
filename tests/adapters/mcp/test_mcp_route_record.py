# tests/adapters/mcp/test_mcp_route_record.py
"""
Тесты для McpRouteRecord — frozen-датакласса маршрута MCP-адаптера.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Дефолты, пользовательские значения, валидация tool_name, frozen,
наследование инвариантов от BaseRouteRecord, конвенция именования
мапперов (response_mapper вместо result_mapper).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import Field

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.contrib.mcp.route_record import McpRouteRecord
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели и действия
# ═════════════════════════════════════════════════════════════════════════════


class SampleParams(BaseParams):
    """Параметры для тестов."""
    name: str = Field(default="test", description="Имя")


class SampleResult(BaseResult):
    """Результат для тестов."""
    value: str = Field(default="ok", description="Значение")


class AltRequest(BaseParams):
    """Альтернативная модель запроса (отличается от SampleParams)."""
    page: int = Field(default=1, description="Страница")


class AltResponse(BaseResult):
    """Альтернативная модель ответа (отличается от SampleResult)."""
    entries: list = Field(default_factory=list, description="Элементы")


@meta(description="Тестовое действие")
@CheckRoles(CheckRoles.NONE)
class SampleAction(BaseAction[SampleParams, SampleResult]):
    """Действие для тестов RouteRecord."""

    @summary_aspect("Тест")
    async def summary(
        self, params: SampleParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> SampleResult:
        return SampleResult()


class NotAnAction:
    """Класс, не наследующий BaseAction."""
    pass


def dummy_params_mapper(x):
    """Тестовый маппер параметров."""
    return x


def dummy_response_mapper(x):
    """Тестовый маппер ответа."""
    return x


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Значения по умолчанию
# ═════════════════════════════════════════════════════════════════════════════


class TestDefaults:
    """Проверка значений по умолчанию для MCP-специфичных полей."""

    def test_default_description_empty(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="test.action")
        assert record.description == ""


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Пользовательские значения полей
# ═════════════════════════════════════════════════════════════════════════════


class TestCustomValues:
    """Проверка установки пользовательских значений MCP-полей."""

    def test_custom_tool_name(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="orders.create")
        assert record.tool_name == "orders.create"

    def test_custom_description(self):
        record = McpRouteRecord(
            action_class=SampleAction,
            tool_name="orders.create",
            description="Создание заказа",
        )
        assert record.description == "Создание заказа"

    def test_full_creation(self):
        """Создание записи с полным набором параметров."""
        record = McpRouteRecord(
            action_class=SampleAction,
            request_model=AltRequest,
            response_model=AltResponse,
            params_mapper=dummy_params_mapper,
            response_mapper=dummy_response_mapper,
            tool_name="orders.update",
            description="Обновление заказа",
        )
        assert record.tool_name == "orders.update"
        assert record.description == "Обновление заказа"
        assert record.effective_request_model is AltRequest
        assert record.effective_response_model is AltResponse

    def test_tool_name_with_dots(self):
        """Имя tool с точками (рекомендуемый формат domain.action)."""
        record = McpRouteRecord(action_class=SampleAction, tool_name="system.health.check")
        assert record.tool_name == "system.health.check"

    def test_tool_name_with_underscores(self):
        """Имя tool с подчёркиваниями."""
        record = McpRouteRecord(action_class=SampleAction, tool_name="create_order")
        assert record.tool_name == "create_order"

    def test_tool_name_with_hyphens(self):
        """Имя tool с дефисами."""
        record = McpRouteRecord(action_class=SampleAction, tool_name="create-order")
        assert record.tool_name == "create-order"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Валидация tool_name
# ═════════════════════════════════════════════════════════════════════════════


class TestToolNameValidation:
    """Валидация имени MCP tool."""

    def test_empty_tool_name_raises_value_error(self):
        with pytest.raises(ValueError, match="tool_name не может быть пустой строкой"):
            McpRouteRecord(action_class=SampleAction, tool_name="")

    def test_whitespace_tool_name_raises_value_error(self):
        with pytest.raises(ValueError, match="tool_name не может быть пустой строкой"):
            McpRouteRecord(action_class=SampleAction, tool_name="   ")

    def test_valid_tool_name_accepted(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="ping")
        assert record.tool_name == "ping"

    def test_single_char_tool_name_accepted(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="x")
        assert record.tool_name == "x"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Frozen
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """Проверка неизменяемости frozen-датакласса."""

    def test_cannot_modify_tool_name(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="test")
        with pytest.raises(FrozenInstanceError):
            record.tool_name = "other"

    def test_cannot_modify_description(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="test")
        with pytest.raises(FrozenInstanceError):
            record.description = "new desc"

    def test_cannot_modify_action_class(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="test")
        with pytest.raises(FrozenInstanceError):
            record.action_class = NotAnAction


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Наследование инвариантов от BaseRouteRecord
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseRouteRecordInvariants:
    """Проверка инвариантов, унаследованных от BaseRouteRecord."""

    def test_auto_extracts_params_type(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="test")
        assert record.params_type is SampleParams

    def test_auto_extracts_result_type(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="test")
        assert record.result_type is SampleResult

    def test_effective_request_model_without_custom(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="test")
        assert record.effective_request_model is SampleParams

    def test_effective_request_model_with_custom(self):
        record = McpRouteRecord(
            action_class=SampleAction, tool_name="test",
            request_model=AltRequest,
            params_mapper=dummy_params_mapper,
        )
        assert record.effective_request_model is AltRequest

    def test_effective_response_model_without_custom(self):
        record = McpRouteRecord(action_class=SampleAction, tool_name="test")
        assert record.effective_response_model is SampleResult

    def test_effective_response_model_with_custom(self):
        record = McpRouteRecord(
            action_class=SampleAction, tool_name="test",
            response_model=AltResponse,
            response_mapper=dummy_response_mapper,
        )
        assert record.effective_response_model is AltResponse

    def test_different_request_model_without_mapper_raises(self):
        with pytest.raises(ValueError, match="params_mapper не указан"):
            McpRouteRecord(
                action_class=SampleAction, tool_name="test",
                request_model=AltRequest,
            )

    def test_different_response_model_without_mapper_raises(self):
        with pytest.raises(ValueError, match="response_mapper не указан"):
            McpRouteRecord(
                action_class=SampleAction, tool_name="test",
                response_model=AltResponse,
            )

    def test_not_base_action_raises_type_error(self):
        with pytest.raises(TypeError, match="подклассом BaseAction"):
            McpRouteRecord(action_class=NotAnAction, tool_name="test")
