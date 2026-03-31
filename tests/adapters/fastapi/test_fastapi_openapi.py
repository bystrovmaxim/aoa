# tests/adapters/fastapi/test_fastapi_openapi.py
"""
Тесты OpenAPI schema, генерируемой FastApiAdapter.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что OpenAPI schema (GET /openapi.json) содержит метаданные,
определённые в коде через Pydantic Field(description=..., examples=...,
gt=..., min_length=..., pattern=...) и декоратор @meta(description=...).

Это ключевое свойство FastApiAdapter: описания полей, constraints,
examples и summary эндпоинтов не пишутся вручную в конфигурации адаптера —
они автоматически извлекаются из Pydantic-моделей Params/Result
и декоратора @meta.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Описания полей (Field description):
    - Каждое поле Params и Result содержит description в OpenAPI schema.
    - Описание совпадает с текстом из Field(description="...").

Constraints (Field gt, min_length, pattern):
    - amount: exclusiveMinimum (gt=0).
    - user_id: minLength (min_length=1).
    - currency: pattern (^[A-Z]{3}$).
    - total: minimum (ge=0).

Examples (Field examples):
    - Поля с examples содержат массив примеров в schema.

Summary эндпоинтов (@meta description):
    - Summary эндпоинта совпадает с description из @meta действия.
    - Если summary указан явно — используется он, а не @meta.

Tags:
    - Теги эндпоинтов совпадают с переданными при регистрации.

Response model:
    - Schema ответа содержит описания полей Result.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
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
@CheckRoles(CheckRoles.NONE, desc="")
class PingAction(BaseAction[EmptyParams, PingResult]):
    """Действие пинга для тестов OpenAPI."""

    @summary_aspect("Pong")
    async def pong(
        self,
        params: EmptyParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> PingResult:
        return PingResult(message="pong")


@meta(description="Создание нового заказа")
@CheckRoles(CheckRoles.NONE, desc="")
class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    """Действие создания заказа для тестов OpenAPI."""

    @regular_aspect("Валидация")
    @ResultStringChecker("validated_user", "Проверенный пользователь", required=True)
    async def validate(
        self,
        params: OrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        return {"validated_user": params.user_id}

    @summary_aspect("Результат")
    async def build_result(
        self,
        params: OrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
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

    adapter = FastApiAdapter(
        machine=machine,
        title="Schema Test API",
        version="2.0.0",
        description="API для проверки OpenAPI schema",
    )

    adapter.get("/api/v1/ping", PingAction, tags=["system"])
    adapter.post(
        "/api/v1/orders",
        CreateOrderAction,
        tags=["orders"],
    )
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
    """Асинхронный HTTP-клиент для запросов к OpenAPI."""
    transport = ASGITransport(app=openapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def openapi_schema(client) -> dict:
    """Загруженная OpenAPI schema как словарь."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции для навигации по OpenAPI schema
# ═════════════════════════════════════════════════════════════════════════════


def _get_path_operation(schema: dict, path: str, method: str = "get") -> dict:
    """
    Извлекает описание операции из OpenAPI schema по пути и методу.

    Аргументы:
        schema: полная OpenAPI schema.
        path: URL-путь эндпоинта (например, "/api/v1/orders").
        method: HTTP-метод в нижнем регистре ("get", "post").

    Возвращает:
        dict — описание операции из schema["paths"][path][method].

    Исключения:
        KeyError: если путь или метод не найдены.
    """
    return schema["paths"][path][method]


def _get_request_body_schema(schema: dict, path: str, method: str = "post") -> dict:
    """
    Извлекает JSON schema тела запроса из OpenAPI schema.

    Навигация: paths → path → method → requestBody → content →
    application/json → schema. Если schema содержит $ref — разрешает
    ссылку через components/schemas.

    Аргументы:
        schema: полная OpenAPI schema.
        path: URL-путь эндпоинта.
        method: HTTP-метод в нижнем регистре.

    Возвращает:
        dict — JSON schema тела запроса с разрешёнными $ref.
    """
    operation = _get_path_operation(schema, path, method)
    content = operation["requestBody"]["content"]["application/json"]["schema"]
    return _resolve_ref(schema, content)


def _get_response_schema(schema: dict, path: str, method: str = "post", status: str = "200") -> dict:
    """
    Извлекает JSON schema ответа из OpenAPI schema.

    Навигация: paths → path → method → responses → status →
    content → application/json → schema. Разрешает $ref.

    Аргументы:
        schema: полная OpenAPI schema.
        path: URL-путь эндпоинта.
        method: HTTP-метод в нижнем регистре.
        status: HTTP-статус код как строка.

    Возвращает:
        dict — JSON schema ответа с разрешёнными $ref.
    """
    operation = _get_path_operation(schema, path, method)
    content = operation["responses"][status]["content"]["application/json"]["schema"]
    return _resolve_ref(schema, content)


def _resolve_ref(schema: dict, obj: dict) -> dict:
    """
    Разрешает $ref ссылку в OpenAPI schema.

    Если объект содержит ключ "$ref" вида "#/components/schemas/ModelName",
    возвращает соответствующую запись из components/schemas.
    Если $ref нет — возвращает объект как есть.

    Аргументы:
        schema: полная OpenAPI schema (для доступа к components).
        obj: объект, который может содержать $ref.

    Возвращает:
        dict — разрешённая schema.
    """
    if "$ref" in obj:
        ref_path = obj["$ref"]  # "#/components/schemas/OrderParams"
        parts = ref_path.lstrip("#/").split("/")
        result = schema
        for part in parts:
            result = result[part]
        return result
    return obj


def _get_property(resolved_schema: dict, property_name: str) -> dict:
    """
    Извлекает описание свойства из разрешённой JSON schema.

    Аргументы:
        resolved_schema: разрешённая schema модели (с полем "properties").
        property_name: имя свойства.

    Возвращает:
        dict — описание свойства (description, type, examples, constraints).
    """
    return resolved_schema["properties"][property_name]


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Метаданные API
# ═════════════════════════════════════════════════════════════════════════════


class TestApiMetadata:
    """Тесты метаданных API в OpenAPI schema."""

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
        """OpenAPI version 3.x."""
        assert openapi_schema["openapi"].startswith("3.")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Summary эндпоинтов из @meta
# ═════════════════════════════════════════════════════════════════════════════


class TestEndpointSummary:
    """Тесты summary эндпоинтов, генерируемого из @meta."""

    @pytest.mark.anyio
    async def test_ping_summary_from_meta(self, openapi_schema):
        """Summary GET /api/v1/ping берётся из @meta(description="Проверка доступности")."""
        operation = _get_path_operation(openapi_schema, "/api/v1/ping", "get")
        assert operation["summary"] == "Проверка доступности"

    @pytest.mark.anyio
    async def test_create_order_summary_from_meta(self, openapi_schema):
        """Summary POST /api/v1/orders берётся из @meta(description="Создание нового заказа")."""
        operation = _get_path_operation(openapi_schema, "/api/v1/orders", "post")
        assert operation["summary"] == "Создание нового заказа"

    @pytest.mark.anyio
    async def test_custom_summary_overrides_meta(self, openapi_schema):
        """Явно указанный summary имеет приоритет над @meta."""
        operation = _get_path_operation(openapi_schema, "/api/v1/orders/custom", "post")
        assert operation["summary"] == "Пользовательский summary"

    @pytest.mark.anyio
    async def test_custom_description(self, openapi_schema):
        """Описание эндпоинта передаётся в OpenAPI."""
        operation = _get_path_operation(openapi_schema, "/api/v1/orders/custom", "post")
        assert operation["description"] == "Подробное описание эндпоинта"

    @pytest.mark.anyio
    async def test_custom_operation_id(self, openapi_schema):
        """operation_id передаётся в OpenAPI."""
        operation = _get_path_operation(openapi_schema, "/api/v1/orders/custom", "post")
        assert operation["operationId"] == "custom_create_order"

    @pytest.mark.anyio
    async def test_deprecated_flag(self, openapi_schema):
        """deprecated=True отображается в OpenAPI."""
        operation = _get_path_operation(openapi_schema, "/api/v1/orders/custom", "post")
        assert operation.get("deprecated") is True


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Tags
# ═════════════════════════════════════════════════════════════════════════════


class TestTags:
    """Тесты тегов эндпоинтов в OpenAPI."""

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
# ТЕСТЫ: Описания полей Params (request body)
# ═════════════════════════════════════════════════════════════════════════════


class TestParamsFieldDescriptions:
    """Тесты описаний полей входных параметров в OpenAPI schema."""

    @pytest.mark.anyio
    async def test_user_id_description(self, openapi_schema):
        """Поле user_id содержит description из Field(description="...")."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "user_id")
        assert prop["description"] == "Идентификатор пользователя"

    @pytest.mark.anyio
    async def test_amount_description(self, openapi_schema):
        """Поле amount содержит description."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "amount")
        assert prop["description"] == "Сумма заказа"

    @pytest.mark.anyio
    async def test_currency_description(self, openapi_schema):
        """Поле currency содержит description."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "currency")
        assert prop["description"] == "Код валюты ISO 4217"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Constraints полей Params
# ═════════════════════════════════════════════════════════════════════════════


class TestParamsConstraints:
    """Тесты constraints полей входных параметров в OpenAPI schema."""

    @pytest.mark.anyio
    async def test_amount_exclusive_minimum(self, openapi_schema):
        """amount с gt=0 → exclusiveMinimum: 0 в OpenAPI."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "amount")
        assert prop.get("exclusiveMinimum") == 0

    @pytest.mark.anyio
    async def test_user_id_min_length(self, openapi_schema):
        """user_id с min_length=1 → minLength: 1 в OpenAPI."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "user_id")
        assert prop.get("minLength") == 1

    @pytest.mark.anyio
    async def test_currency_pattern(self, openapi_schema):
        """currency с pattern=^[A-Z]{3}$ → pattern в OpenAPI."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "currency")
        assert prop.get("pattern") == "^[A-Z]{3}$"

    @pytest.mark.anyio
    async def test_currency_default(self, openapi_schema):
        """currency с default="RUB" → default: "RUB" в OpenAPI."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "currency")
        assert prop.get("default") == "RUB"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Examples полей Params
# ═════════════════════════════════════════════════════════════════════════════


class TestParamsExamples:
    """Тесты examples полей входных параметров в OpenAPI schema."""

    @pytest.mark.anyio
    async def test_user_id_examples(self, openapi_schema):
        """user_id содержит examples из Field(examples=["user_123"])."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "user_id")
        assert "examples" in prop
        assert "user_123" in prop["examples"]

    @pytest.mark.anyio
    async def test_amount_examples(self, openapi_schema):
        """amount содержит examples из Field(examples=[1500.0, 99.99])."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "amount")
        assert "examples" in prop
        assert 1500.0 in prop["examples"]
        assert 99.99 in prop["examples"]

    @pytest.mark.anyio
    async def test_currency_examples(self, openapi_schema):
        """currency содержит examples из Field(examples=["RUB", "USD", "EUR"])."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(body_schema, "currency")
        assert "examples" in prop
        assert "RUB" in prop["examples"]
        assert "USD" in prop["examples"]


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Описания и constraints полей Result (response)
# ═════════════════════════════════════════════════════════════════════════════


class TestResultFields:
    """Тесты описаний и constraints полей Result в OpenAPI schema."""

    @pytest.mark.anyio
    async def test_order_id_description(self, openapi_schema):
        """Поле order_id в ответе содержит description."""
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "order_id")
        assert prop["description"] == "ID созданного заказа"

    @pytest.mark.anyio
    async def test_status_description(self, openapi_schema):
        """Поле status в ответе содержит description."""
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "status")
        assert prop["description"] == "Статус заказа"

    @pytest.mark.anyio
    async def test_total_description(self, openapi_schema):
        """Поле total в ответе содержит description."""
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "total")
        assert prop["description"] == "Итоговая сумма"

    @pytest.mark.anyio
    async def test_total_minimum_constraint(self, openapi_schema):
        """total с ge=0 → minimum: 0 в OpenAPI."""
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "total")
        assert prop.get("minimum") == 0

    @pytest.mark.anyio
    async def test_order_id_examples(self, openapi_schema):
        """Поле order_id в ответе содержит examples."""
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/orders")
        prop = _get_property(resp_schema, "order_id")
        assert "examples" in prop
        assert "ORD-1" in prop["examples"]

    @pytest.mark.anyio
    async def test_ping_result_message_description(self, openapi_schema):
        """Поле message в PingResult содержит description."""
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/ping", method="get")
        prop = _get_property(resp_schema, "message")
        assert prop["description"] == "Ответное сообщение"

    @pytest.mark.anyio
    async def test_ping_result_message_examples(self, openapi_schema):
        """Поле message в PingResult содержит examples."""
        resp_schema = _get_response_schema(openapi_schema, "/api/v1/ping", method="get")
        prop = _get_property(resp_schema, "message")
        assert "examples" in prop
        assert "pong" in prop["examples"]


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Обязательные поля (required)
# ═════════════════════════════════════════════════════════════════════════════


class TestRequiredFields:
    """Тесты обязательности полей в OpenAPI schema."""

    @pytest.mark.anyio
    async def test_user_id_is_required(self, openapi_schema):
        """user_id без default → required в OpenAPI."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        assert "user_id" in body_schema.get("required", [])

    @pytest.mark.anyio
    async def test_amount_is_required(self, openapi_schema):
        """amount без default → required в OpenAPI."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        assert "amount" in body_schema.get("required", [])

    @pytest.mark.anyio
    async def test_currency_is_not_required(self, openapi_schema):
        """currency с default="RUB" → НЕ required в OpenAPI."""
        body_schema = _get_request_body_schema(openapi_schema, "/api/v1/orders")
        required = body_schema.get("required", [])
        assert "currency" not in required


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Наличие всех путей
# ═════════════════════════════════════════════════════════════════════════════


class TestPathsPresence:
    """Тесты наличия всех зарегистрированных путей в OpenAPI."""

    @pytest.mark.anyio
    async def test_all_paths_present(self, openapi_schema):
        """Все зарегистрированные пути присутствуют в schema."""
        paths = openapi_schema["paths"]
        assert "/api/v1/ping" in paths
        assert "/api/v1/orders" in paths
        assert "/api/v1/orders/custom" in paths
        assert "/health" in paths

    @pytest.mark.anyio
    async def test_ping_is_get(self, openapi_schema):
        """Ping зарегистрирован как GET."""
        assert "get" in openapi_schema["paths"]["/api/v1/ping"]

    @pytest.mark.anyio
    async def test_orders_is_post(self, openapi_schema):
        """Orders зарегистрирован как POST."""
        assert "post" in openapi_schema["paths"]["/api/v1/orders"]

    @pytest.mark.anyio
    async def test_health_is_get(self, openapi_schema):
        """Health check зарегистрирован как GET."""
        assert "get" in openapi_schema["paths"]["/health"]
