# tests/adapters/fastapi/test_fastapi_route_record.py
"""
Тесты для FastApiRouteRecord — frozen-датакласса маршрута FastAPI-адаптера.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Дефолты, пользовательские значения, валидация method, валидация path,
frozen, наследование инвариантов от BaseRouteRecord, конвенция
именования мапперов (response_mapper вместо result_mapper).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import Field

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.contrib.fastapi.route_record import FastApiRouteRecord
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
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
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
    """Проверка значений по умолчанию для HTTP-специфичных полей."""

    def test_default_method_is_post(self):
        record = FastApiRouteRecord(action_class=SampleAction)
        assert record.method == "POST"

    def test_default_path_is_slash(self):
        record = FastApiRouteRecord(action_class=SampleAction)
        assert record.path == "/"

    def test_default_tags_empty_tuple(self):
        record = FastApiRouteRecord(action_class=SampleAction)
        assert record.tags == ()

    def test_default_summary_empty(self):
        record = FastApiRouteRecord(action_class=SampleAction)
        assert record.summary == ""

    def test_default_description_empty(self):
        record = FastApiRouteRecord(action_class=SampleAction)
        assert record.description == ""

    def test_default_operation_id_none(self):
        record = FastApiRouteRecord(action_class=SampleAction)
        assert record.operation_id is None

    def test_default_deprecated_false(self):
        record = FastApiRouteRecord(action_class=SampleAction)
        assert record.deprecated is False


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Пользовательские значения полей
# ═════════════════════════════════════════════════════════════════════════════


class TestCustomValues:
    """Проверка установки пользовательских значений HTTP-полей."""

    def test_custom_method(self):
        record = FastApiRouteRecord(action_class=SampleAction, method="GET", path="/test")
        assert record.method == "GET"

    def test_custom_path(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/api/v1/orders")
        assert record.path == "/api/v1/orders"

    def test_path_with_parameter(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/orders/{order_id}")
        assert record.path == "/orders/{order_id}"

    def test_custom_tags(self):
        record = FastApiRouteRecord(
            action_class=SampleAction, path="/test",
            tags=("orders", "admin"),
        )
        assert record.tags == ("orders", "admin")

    def test_custom_summary(self):
        record = FastApiRouteRecord(
            action_class=SampleAction, path="/test",
            summary="Создание заказа",
        )
        assert record.summary == "Создание заказа"

    def test_custom_description(self):
        record = FastApiRouteRecord(
            action_class=SampleAction, path="/test",
            description="Подробное описание эндпоинта",
        )
        assert record.description == "Подробное описание эндпоинта"

    def test_custom_operation_id(self):
        record = FastApiRouteRecord(
            action_class=SampleAction, path="/test",
            operation_id="create_order",
        )
        assert record.operation_id == "create_order"

    def test_custom_deprecated(self):
        record = FastApiRouteRecord(
            action_class=SampleAction, path="/test",
            deprecated=True,
        )
        assert record.deprecated is True

    def test_full_creation(self):
        """Создание записи с полным набором параметров."""
        record = FastApiRouteRecord(
            action_class=SampleAction,
            request_model=AltRequest,
            response_model=AltResponse,
            params_mapper=dummy_params_mapper,
            response_mapper=dummy_response_mapper,
            method="PUT",
            path="/api/v1/orders/{id}",
            tags=("orders", "update"),
            summary="Обновление заказа",
            description="Обновляет существующий заказ.",
            operation_id="update_order",
            deprecated=False,
        )
        assert record.method == "PUT"
        assert record.path == "/api/v1/orders/{id}"
        assert record.tags == ("orders", "update")
        assert record.summary == "Обновление заказа"
        assert record.operation_id == "update_order"
        assert record.effective_request_model is AltRequest
        assert record.effective_response_model is AltResponse


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Нормализация и валидация method
# ═════════════════════════════════════════════════════════════════════════════


class TestMethodValidation:
    """Валидация HTTP-метода."""

    @pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE", "PATCH"])
    def test_allowed_methods(self, method):
        """Все допустимые HTTP-методы принимаются."""
        record = FastApiRouteRecord(action_class=SampleAction, method=method, path="/test")
        assert record.method == method

    @pytest.mark.parametrize("method,expected", [
        ("get", "GET"),
        ("post", "POST"),
        ("put", "PUT"),
        ("delete", "DELETE"),
        ("patch", "PATCH"),
        ("Get", "GET"),
        ("Post", "POST"),
    ])
    def test_method_normalized_to_uppercase(self, method, expected):
        """Метод приводится к верхнему регистру."""
        record = FastApiRouteRecord(action_class=SampleAction, method=method, path="/test")
        assert record.method == expected

    @pytest.mark.parametrize("method", ["HEAD", "OPTIONS", "TRACE", "CONNECT", "UNKNOWN", ""])
    def test_invalid_method_raises_value_error(self, method):
        """Недопустимый HTTP-метод → ValueError."""
        with pytest.raises(ValueError, match="method должен быть одним из"):
            FastApiRouteRecord(action_class=SampleAction, method=method, path="/test")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Валидация path
# ═════════════════════════════════════════════════════════════════════════════


class TestPathValidation:
    """Валидация URL-пути эндпоинта."""

    def test_empty_path_raises_value_error(self):
        with pytest.raises(ValueError, match="path не может быть пустой строкой"):
            FastApiRouteRecord(action_class=SampleAction, path="")

    def test_whitespace_path_raises_value_error(self):
        with pytest.raises(ValueError, match="path не может быть пустой строкой"):
            FastApiRouteRecord(action_class=SampleAction, path="   ")

    def test_path_without_leading_slash_raises_value_error(self):
        with pytest.raises(ValueError, match="path должен начинаться с '/'"):
            FastApiRouteRecord(action_class=SampleAction, path="api/v1/orders")

    def test_valid_path_accepted(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/api/v1/orders")
        assert record.path == "/api/v1/orders"

    def test_root_path_accepted(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/")
        assert record.path == "/"

    def test_path_with_multiple_parameters(self):
        record = FastApiRouteRecord(
            action_class=SampleAction,
            path="/api/v1/{domain}/orders/{order_id}",
        )
        assert record.path == "/api/v1/{domain}/orders/{order_id}"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Frozen
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """Проверка неизменяемости frozen-датакласса."""

    def test_cannot_modify_method(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        with pytest.raises(FrozenInstanceError):
            record.method = "GET"

    def test_cannot_modify_path(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        with pytest.raises(FrozenInstanceError):
            record.path = "/other"

    def test_cannot_modify_tags(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        with pytest.raises(FrozenInstanceError):
            record.tags = ("new",)

    def test_cannot_modify_action_class(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        with pytest.raises(FrozenInstanceError):
            record.action_class = NotAnAction

    def test_cannot_modify_summary(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        with pytest.raises(FrozenInstanceError):
            record.summary = "new"

    def test_cannot_modify_deprecated(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        with pytest.raises(FrozenInstanceError):
            record.deprecated = True


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Наследование инвариантов от BaseRouteRecord
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseRouteRecordInvariants:
    """Проверка инвариантов, унаследованных от BaseRouteRecord."""

    def test_auto_extracts_params_type(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        assert record.params_type is SampleParams

    def test_auto_extracts_result_type(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        assert record.result_type is SampleResult

    def test_effective_request_model_without_custom(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        assert record.effective_request_model is SampleParams

    def test_effective_request_model_with_custom(self):
        record = FastApiRouteRecord(
            action_class=SampleAction, path="/test",
            request_model=AltRequest,
            params_mapper=dummy_params_mapper,
        )
        assert record.effective_request_model is AltRequest

    def test_effective_response_model_without_custom(self):
        record = FastApiRouteRecord(action_class=SampleAction, path="/test")
        assert record.effective_response_model is SampleResult

    def test_effective_response_model_with_custom(self):
        record = FastApiRouteRecord(
            action_class=SampleAction, path="/test",
            response_model=AltResponse,
            response_mapper=dummy_response_mapper,
        )
        assert record.effective_response_model is AltResponse

    def test_different_request_model_without_mapper_raises(self):
        with pytest.raises(ValueError, match="params_mapper не указан"):
            FastApiRouteRecord(
                action_class=SampleAction, path="/test",
                request_model=AltRequest,
            )

    def test_different_response_model_without_mapper_raises(self):
        with pytest.raises(ValueError, match="response_mapper не указан"):
            FastApiRouteRecord(
                action_class=SampleAction, path="/test",
                response_model=AltResponse,
            )

    def test_not_base_action_raises_type_error(self):
        with pytest.raises(TypeError, match="подклассом BaseAction"):
            FastApiRouteRecord(action_class=NotAnAction, path="/test")
