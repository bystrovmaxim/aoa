# tests/adapters/fastapi/test_fastapi_openapi.py
"""
Тесты OpenAPI schema, генерируемой FastApiAdapter.

Проверяет, что OpenAPI schema содержит метаданные из Pydantic
Field(description=..., examples=..., gt=..., min_length=..., pattern=...)
и декоратора @meta(description=...).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.auth.no_auth_coordinator import NoAuthCoordinator
from action_machine.checkers.result_string_checker import ResultStringChecker
from action_machine.contrib.fastapi import FastApiAdapter
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели и действия
# ═════════════════════════════════════════════════════════════════════════════


class EmptyParams(BaseParams):
    """Пустые параметры."""
    pass


class PingResult(BaseResult):
    """Результат пинга с описанием поля."""
    message: str = Field(description="Ответное сообщение", examples=["pong"])


class OrderParams(BaseParams):
    """Параметры заказа с constraints и examples."""
    user_id: str = Field(
        description="Идентификатор пользователя",
        min_length=1,
        examples=["user_123"],
    )
    amount: float = Field(
        description="Сумма заказа",
        gt=0,
        examples=[1500.0, 99.99],
    )
    currency: str = Field(
        default="RUB",
        description="Код валюты ISO 4217",
        pattern=r"^[A-Z]{3}$",
        examples=["RUB", "USD", "EUR"],
    )


class OrderResult(BaseResult):
    """Результат заказа с описаниями и constraints."""
    order_id: str = Field(description="ID созданного заказа", examples=["ORD-1"])
    status: str = Field(description="Статус заказа", examples=["created"])
    total: float = Field(description="Итоговая сумма", ge=0, examples=[1500.0])


@meta(description="Проверка доступности")
@CheckRoles(CheckRoles.NONE)
class PingAction(BaseAction[EmptyParams, PingResult]):
    @summary_aspect("Pong")
    async def pong(
        self, params: EmptyParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> PingResult:
        return PingResult(message="pong")


@meta(description="Создание нового заказа")
@CheckRoles(CheckRoles.NONE)
class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    @regular_aspect("Валидация")
    @ResultStringChecker("validated_user", required=True)
    async def validate(
        self, params: OrderParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> dict:
        return {"validated_user": params.user_id}

    @summary_aspect("Результат")
    async def build_result(
        self, params: OrderParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> OrderResult:
        return OrderResult(order_id="ORD-1", status="created", total=params.amount)


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def openapi_app():
    """FastAPI-приложение с зарегистрированными маршрутами для проверки schema."""
    coordinator = GateCoordinator()
    machine = ActionProductMachine(
        mode="test",
        coordinator=coordinator,
        log_coordinator=AsyncMock(),
    )
    auth = NoAuthCoordinator()

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=auth,
        title="Schema Test API",
        version="2.0.0",
        description="API для проверки OpenAPI schema",
    )

    adapter.get("/api/v1/ping", PingAction, tags=["system"])
    adapter.post("/api/v1/orders", CreateOrderAction, tags=["orders"])
    adapter.post(
        "/api/v1/orders/custom",
        CreateOrderAction,
        tags=["orders", "custom"],
        summary="Пользовательский summary",
        description="Подробное описание эндпоинта",
        operation_id="custom_create_order",
        deprecated=True,
    )

    return adapter.build()


@pytest.fixture
async def client(openapi_app):
    transport = ASGITransport(app=openapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def openapi_schema(client) -> dict:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═════════════════════════════════════════════════════════════════════════════


def _get_path_operation(schema: dict, path: str, method: str = "get") -> dict:
    return schema["paths"][path][method]


def _get_request_body_schema(schema: dict, path: str, method: str = "post") -> dict:
    operation = _get_path_operation(schema, path, method)
    content = operation["requestBody"]["content"]["application/json"]["schema"]
    return _resolve_ref(schema, content)


def _get_response_schema(schema: dict, path: str, method: str = "post", status: str = "200") -> dict:
    operation = _get_path_operation(schema, path, method)
    content = operation["responses"][status]["content"]["application/json"]["schema"]
    return _resolve_ref(schema, content)


def _resolve_ref(schema: dict, obj: dict) -> dict:
    if "$ref" in obj:
        ref_path = obj["$ref"]
        parts = ref_path.lstrip("#/").split("/")
        result = schema
        for part in parts:
            result = result[part]
        return result
    return obj


def _get_property(resolved_schema: dict, property_name: str) -> dict:
    return resolved_schema["properties"][property_name]


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Метаданные API
# ═════════════════════════════════════════════════════════════════════════════


class TestApiMetadata:
    @pytest.mark.anyio
    async def test_api_title(self, openapi_schema):
        assert openapi_schema["info"]["title"] == "Schema Test API"

    @pytest.mark.anyio
    async def test_api_version(self, openapi_schema):
        assert openapi_schema["info"]["version"] == "2.0.0"

    @pytest.mark.anyio
    async def test_api_description(self, openapi_schema):
        assert openapi_schema["info"]["description"] == "API для проверки OpenAPI schema"

    @pytest.mark.anyio
    async def test_openapi_version(self, openapi_schema):
        assert openapi_schema["openapi"].startswith("3.")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Summary эндпоинтов из @meta
# ═════════════════════════════════════════════════════════════════════════════


class TestEndpointSummary:
    @pytest.mark.anyio
    async def test_ping_summary_from_meta(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/api/v1/ping", "get")
        assert operation["summary"] == "Проверка доступности"

    @pytest.mark.anyio
    async def test_create_order_summary_from_meta(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/api/v1/orders", "post")
        assert operation["summary"] == "Создание нового заказа"

    @pytest.mark.anyio
    async def test_custom_summary_overrides_meta(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/api/v1/orders/custom", "post")
        assert operation["summary"] == "Пользовательский summary"

    @pytest.mark.anyio
    async def test_custom_description(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/api/v1/orders/custom", "post")
        assert operation["description"] == "Подробное описание эндпоинта"

    @pytest.mark.anyio
    async def test_custom_operation_id(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/api/v1/orders/custom", "post")
        assert operation["operationId"] == "custom_create_order"

    @pytest.mark.anyio
    async def test_deprecated_flag(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/api/v1/orders/custom", "post")
        assert operation.get("deprecated") is True


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Tags
# ═════════════════════════════════════════════════════════════════════════════


class TestTags:
    @pytest.mark.anyio
    async def test_ping_tags(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/api/v1/ping", "get")
        assert "system" in operation["tags"]

    @pytest.mark.anyio
    async def test_orders_tags(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/api/v1/orders", "post")
        assert "orders" in operation["tags"]

    @pytest.mark.anyio
    async def test_custom_multiple_tags(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/api/v1/orders/custom", "post")
        assert "orders" in operation["tags"]
        assert "custom" in operation["tags"]

    @pytest.mark.anyio
    async def test_health_system_tag(self, openapi_schema):
        operation = _get_path_operation(openapi_schema, "/health", "get")
        assert "system" in operation["tags"]


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Описания полей Params
# ═════════════════════════════════════════════════════════════════════════════


class TestParamsFieldDescriptions:
    @pytest.mark.anyio
    async def test_user_id_description(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "user_id")
        assert prop["description"] == "Идентификатор пользователя"

    @pytest.mark.anyio
    async def test_amount_description(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "amount")
        assert prop["description"] == "Сумма заказа"

    @pytest.mark.anyio
    async def test_currency_description(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "currency")
        assert prop["description"] == "Код валюты ISO 4217"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Constraints полей Params
# ═════════════════════════════════════════════════════════════════════════════


class TestParamsConstraints:
    @pytest.mark.anyio
    async def test_amount_exclusive_minimum(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "amount")
        assert prop.get("exclusiveMinimum") == 0

    @pytest.mark.anyio
    async def test_user_id_min_length(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "user_id")
        assert prop.get("minLength") == 1

    @pytest.mark.anyio
    async def test_currency_pattern(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "currency")
        assert prop.get("pattern") == "^[A-Z]{3}$"

    @pytest.mark.anyio
    async def test_currency_default(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "currency")
        assert prop.get("default") == "RUB"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Examples полей Params
# ═════════════════════════════════════════════════════════════════════════════


class TestParamsExamples:
    @pytest.mark.anyio
    async def test_user_id_examples(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "user_id")
        assert "examples" in prop
        assert "user_123" in prop["examples"]

    @pytest.mark.anyio
    async def test_amount_examples(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "amount")
        assert "examples" in prop
        assert 1500.0 in prop["examples"]
        assert 99.99 in prop["examples"]

    @pytest.mark.anyio
    async def test_currency_examples(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "currency")
        assert "examples" in prop
        assert "RUB" in prop["examples"]
        assert "USD" in prop["examples"]


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Описания и constraints полей Result
# ═════════════════════════════════════════════════════════════════════════════


class TestResultFields:
    @pytest.mark.anyio
    async def test_order_id_description(self, openapi_schema):
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "order_id")
        assert prop["description"] == "ID созданного заказа"

    @pytest.mark.anyio
    async def test_status_description(self, openapi_schema):
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "status")
        assert prop["description"] == "Статус заказа"

    @pytest.mark.anyio
    async def test_total_description(self, openapi_schema):
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "total")
        assert prop["description"] == "Итоговая сумма"

    @pytest.mark.anyio
    async def test_total_minimum_constraint(self, openapi_schema):
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "total")
        assert prop.get("minimum") == 0

    @pytest.mark.anyio
    async def test_order_id_examples(self, openapi_schema):
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "order_id")
        assert "examples" in prop
        assert "ORD-1" in prop["examples"]

    @pytest.mark.anyio
    async def test_ping_result_message_description(self, openapi_schema):
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/ping", method="get")
        prop = _get_property(resp_schema, "message")
        assert prop["description"] == "Ответное сообщение"

    @pytest.mark.anyio
    async def test_ping_result_message_examples(self, openapi_schema):
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/ping", method="get")
        prop = _get_property(resp_schema, "message")
        assert "examples" in prop
        assert "pong" in prop["examples"]


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Обязательные поля
# ═════════════════════════════════════════════════════════════════════════════


class TestRequiredFields:
    @pytest.mark.anyio
    async def test_user_id_is_required(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        assert "user_id" in body_schema.get("required", [])

    @pytest.mark.anyio
    async def test_amount_is_required(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        assert "amount" in body_schema.get("required", [])

    @pytest.mark.anyio
    async def test_currency_is_not_required(self, openapi_schema):
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        required = body_schema.get("required", [])
        assert "currency" not in required


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Наличие всех путей
# ═════════════════════════════════════════════════════════════════════════════


class TestPathsPresence:
    @pytest.mark.anyio
    async def test_all_paths_present(self, openapi_schema):
        paths = openapi_schema["paths"]
        assert "/api/v1/ping" in paths
        assert "/api/v1/orders" in paths
        assert "/api/v1/orders/custom" in paths
        assert "/health" in paths

    @pytest.mark.anyio
    async def test_ping_is_get(self, openapi_schema):
        assert "get" in openapi_schema["paths"]["/api/v1/ping"]

    @pytest.mark.anyio
    async def test_orders_is_post(self, openapi_schema):
        assert "post" in openapi_schema["paths"]["/api/v1/orders"]

    @pytest.mark.anyio
    async def test_health_is_get(self, openapi_schema):
        assert "get" in openapi_schema["paths"]["/health"]
