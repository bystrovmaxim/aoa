# tests/adapters/fastapi/test_fastapi_adapter.py
"""
Тесты для FastApiAdapter — HTTP-адаптера ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Конструктор:
    - Корректная инициализация с machine, title, version, description.
    - TypeError при передаче не-ActionProductMachine.

Протокольные методы (post, get, put, delete, patch):
    - Регистрация маршрутов с минимальными параметрами.
    - Регистрация с tags, summary, description, operation_id, deprecated.
    - Auto-summary из @meta действия.
    - Множественные маршруты.
    - Fluent chain: методы возвращают self.

build():
    - Возвращает FastAPI-приложение.
    - Health check эндпоинт /health доступен.
    - Зарегистрированные эндпоинты доступны.

Endpoint-тесты через httpx:
    - POST с валидными данными → 200 + result.
    - POST с невалидными данными (нарушение constraints) → 422.
    - GET /health → 200 {"status": "ok"}.
    - GET /api/v1/ping → 200 {"message": "pong"}.
    - GET с path-параметром → 200.

Exception handlers:
    - AuthorizationError → 403.
    - ValidationFieldError → 422.
    - Необработанное исключение → 500.

Маппинг:
    - Route с params_mapper — маппер вызывается.
    - Route с response_mapper — маппер вызывается.

Fluent chain:
    - Цепочечная регистрация маршрутов.
    - Цепочка завершается build().
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
from action_machine.core.exceptions import ValidationFieldError
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели и действия
# ═════════════════════════════════════════════════════════════════════════════


class EmptyParams(BaseParams):
    """Пустые параметры."""
    pass


class PingResult(BaseResult):
    """Результат пинга."""
    message: str = Field(default="pong", description="Ответ")


class OrderParams(BaseParams):
    """Параметры заказа с constraints."""
    user_id: str = Field(description="ID пользователя", min_length=1, examples=["user_1"])
    amount: float = Field(description="Сумма", gt=0, examples=[100.0])
    currency: str = Field(default="RUB", description="Валюта", pattern=r"^[A-Z]{3}$")


class OrderResult(BaseResult):
    """Результат создания заказа."""
    order_id: str = Field(description="ID заказа", examples=["ORD-1"])
    status: str = Field(description="Статус", examples=["created"])
    total: float = Field(description="Итого", ge=0)


class GetOrderParams(BaseParams):
    """Параметры получения заказа."""
    order_id: str = Field(description="ID заказа", min_length=1)


class AltRequest(BaseParams):
    """Альтернативная модель запроса для тестов маппинга."""
    raw_data: str = Field(default="raw", description="Сырые данные")


class AltResponse(BaseResult):
    """Альтернативная модель ответа для тестов маппинга."""
    transformed: str = Field(default="done", description="Преобразованные данные")


# ── Действия ───────────────────────────────────────────────────────────────


@meta(description="Проверка доступности сервиса")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class PingAction(BaseAction[EmptyParams, PingResult]):
    @summary_aspect("Pong")
    async def pong(self, params, state, box, connections):
        return PingResult(message="pong")


@meta(description="Создание заказа")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    @regular_aspect("Валидация")
    @ResultStringChecker("validated_user", "Проверенный пользователь", required=True)
    async def validate(self, params, state, box, connections):
        return {"validated_user": params.user_id}

    @summary_aspect("Результат")
    async def build_result(self, params, state, box, connections):
        return OrderResult(
            order_id=f"ORD-{params.user_id}",
            status="created",
            total=params.amount,
        )


@meta(description="Получение заказа")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class GetOrderAction(BaseAction[GetOrderParams, OrderResult]):
    @summary_aspect("Загрузка заказа")
    async def get(self, params, state, box, connections):
        return OrderResult(
            order_id=params.order_id,
            status="created",
            total=1500.0,
        )


@meta(description="Действие с ошибкой авторизации")
@CheckRoles("admin", desc="Только админ")
class AuthErrorAction(BaseAction[EmptyParams, PingResult]):
    @summary_aspect("Никогда не выполнится")
    async def summary(self, params, state, box, connections):
        return PingResult(message="unreachable")


@meta(description="Действие с ошибкой валидации")
@CheckRoles(CheckRoles.NONE, desc="")
class ValidationErrorAction(BaseAction[EmptyParams, PingResult]):
    @summary_aspect("Бросает ValidationFieldError")
    async def summary(self, params, state, box, connections):
        raise ValidationFieldError("Поле 'amount' невалидно", field="amount")


@meta(description="Действие с необработанным исключением")
@CheckRoles(CheckRoles.NONE, desc="")
class InternalErrorAction(BaseAction[EmptyParams, PingResult]):
    @summary_aspect("Бросает RuntimeError")
    async def summary(self, params, state, box, connections):
        raise RuntimeError("Внутренняя ошибка")


@meta(description="Действие для теста маппинга")
@CheckRoles(CheckRoles.NONE, desc="")
class MappableAction(BaseAction[OrderParams, OrderResult]):
    @summary_aspect("Маппинг")
    async def summary(self, params, state, box, connections):
        return OrderResult(
            order_id=f"ORD-{params.user_id}",
            status="mapped",
            total=params.amount,
        )


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def coordinator() -> GateCoordinator:
    return GateCoordinator()


@pytest.fixture
def machine(coordinator) -> ActionProductMachine:
    return ActionProductMachine(
        mode="test",
        coordinator=coordinator,
        log_coordinator=AsyncMock(),
    )


@pytest.fixture
def adapter(machine) -> FastApiAdapter:
    return FastApiAdapter(
        machine=machine,
        title="Test API",
        version="1.0.0",
        description="API для тестов",
    )


@pytest.fixture
def app_with_routes(adapter) -> FastApiAdapter:
    """Адаптер с зарегистрированными маршрутами (до build)."""
    adapter.get("/api/v1/ping", PingAction, tags=["system"])
    adapter.post("/api/v1/orders", CreateOrderAction, tags=["orders"])
    adapter.get("/api/v1/orders/{order_id}", GetOrderAction, tags=["orders"])
    return adapter


@pytest.fixture
def app(app_with_routes):
    """Готовое FastAPI-приложение."""
    return app_with_routes.build()


@pytest.fixture
async def client(app):
    """Асинхронный HTTP-клиент для тестирования."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Конструктор
# ═════════════════════════════════════════════════════════════════════════════


class TestConstructor:
    """Тесты конструктора FastApiAdapter."""

    def test_stores_title(self, adapter):
        assert adapter.title == "Test API"

    def test_stores_version(self, adapter):
        assert adapter.version == "1.0.0"

    def test_stores_description(self, adapter):
        assert adapter.api_description == "API для тестов"

    def test_default_title(self, machine):
        a = FastApiAdapter(machine=machine)
        assert a.title == "ActionMachine API"

    def test_default_version(self, machine):
        a = FastApiAdapter(machine=machine)
        assert a.version == "0.1.0"

    def test_default_description(self, machine):
        a = FastApiAdapter(machine=machine)
        assert a.api_description == ""

    def test_non_machine_raises_type_error(self):
        with pytest.raises(TypeError, match="ожидает ActionProductMachine"):
            FastApiAdapter(machine="not a machine")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Регистрация маршрутов
# ═════════════════════════════════════════════════════════════════════════════


class TestRouteRegistration:
    """Тесты протокольных методов регистрации."""

    def test_post_registers_route(self, adapter):
        adapter.post("/test", PingAction)
        assert len(adapter.routes) == 1
        assert adapter.routes[0].method == "POST"
        assert adapter.routes[0].path == "/test"

    def test_get_registers_route(self, adapter):
        adapter.get("/test", PingAction)
        assert len(adapter.routes) == 1
        assert adapter.routes[0].method == "GET"

    def test_put_registers_route(self, adapter):
        adapter.put("/test", PingAction)
        assert adapter.routes[0].method == "PUT"

    def test_delete_registers_route(self, adapter):
        adapter.delete("/test", PingAction)
        assert adapter.routes[0].method == "DELETE"

    def test_patch_registers_route(self, adapter):
        adapter.patch("/test", PingAction)
        assert adapter.routes[0].method == "PATCH"

    def test_multiple_routes(self, adapter):
        adapter.get("/a", PingAction)
        adapter.post("/b", CreateOrderAction)
        adapter.get("/c", GetOrderAction)
        assert len(adapter.routes) == 3

    def test_tags_passed_to_record(self, adapter):
        adapter.post("/test", PingAction, tags=["system", "ping"])
        assert adapter.routes[0].tags == ("system", "ping")

    def test_summary_passed_to_record(self, adapter):
        adapter.post("/test", PingAction, summary="Пользовательский summary")
        assert adapter.routes[0].summary == "Пользовательский summary"

    def test_auto_summary_from_meta(self, adapter):
        """Если summary не указан — берётся из @meta."""
        adapter.post("/test", PingAction)
        assert adapter.routes[0].summary == "Проверка доступности сервиса"

    def test_explicit_summary_overrides_meta(self, adapter):
        """Явный summary имеет приоритет над @meta."""
        adapter.post("/test", PingAction, summary="Custom")
        assert adapter.routes[0].summary == "Custom"

    def test_operation_id_passed(self, adapter):
        adapter.post("/test", PingAction, operation_id="my_ping")
        assert adapter.routes[0].operation_id == "my_ping"

    def test_deprecated_passed(self, adapter):
        adapter.post("/test", PingAction, deprecated=True)
        assert adapter.routes[0].deprecated is True

    def test_description_passed(self, adapter):
        adapter.post("/test", PingAction, description="Подробное описание")
        assert adapter.routes[0].description == "Подробное описание"

    def test_post_returns_self(self, adapter):
        """post() возвращает self для fluent chain."""
        result = adapter.post("/test", PingAction)
        assert result is adapter

    def test_get_returns_self(self, adapter):
        """get() возвращает self для fluent chain."""
        result = adapter.get("/test", PingAction)
        assert result is adapter

    def test_put_returns_self(self, adapter):
        """put() возвращает self для fluent chain."""
        result = adapter.put("/test", PingAction)
        assert result is adapter

    def test_delete_returns_self(self, adapter):
        """delete() возвращает self для fluent chain."""
        result = adapter.delete("/test", PingAction)
        assert result is adapter

    def test_patch_returns_self(self, adapter):
        """patch() возвращает self для fluent chain."""
        result = adapter.patch("/test", PingAction)
        assert result is adapter

    def test_fluent_chain(self, adapter):
        """Цепочечная регистрация маршрутов."""
        result = adapter \
            .get("/a", PingAction, tags=["system"]) \
            .post("/b", CreateOrderAction, tags=["orders"]) \
            .get("/c", GetOrderAction, tags=["orders"])

        assert result is adapter
        assert len(adapter.routes) == 3


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: build()
# ═════════════════════════════════════════════════════════════════════════════


class TestBuild:
    """Тесты метода build()."""

    def test_returns_fastapi_instance(self, app):
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_app_title(self, app):
        assert app.title == "Test API"

    def test_app_version(self, app):
        assert app.version == "1.0.0"

    def test_app_has_routes(self, app):
        paths = [route.path for route in app.routes]
        assert "/api/v1/ping" in paths
        assert "/api/v1/orders" in paths
        assert "/api/v1/orders/{order_id}" in paths
        assert "/health" in paths

    def test_fluent_chain_to_build(self, machine):
        """Fluent chain завершается build()."""
        adapter = FastApiAdapter(machine=machine, title="Chain API")
        app = adapter \
            .get("/ping", PingAction, tags=["system"]) \
            .post("/orders", CreateOrderAction, tags=["orders"]) \
            .build()

        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
        paths = [route.path for route in app.routes]
        assert "/ping" in paths
        assert "/orders" in paths


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: HTTP-эндпоинты через httpx
# ═════════════════════════════════════════════════════════════════════════════


class TestEndpoints:
    """Тесты HTTP-эндпоинтов через AsyncClient."""

    @pytest.mark.anyio
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.anyio
    async def test_ping(self, client):
        response = await client.get("/api/v1/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"

    @pytest.mark.anyio
    async def test_create_order_success(self, client):
        response = await client.post(
            "/api/v1/orders",
            json={"user_id": "user_42", "amount": 1500.0, "currency": "RUB"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "ORD-user_42"
        assert data["status"] == "created"
        assert data["total"] == 1500.0

    @pytest.mark.anyio
    async def test_create_order_invalid_amount(self, client):
        """amount <= 0 нарушает constraint gt=0 → 422."""
        response = await client.post(
            "/api/v1/orders",
            json={"user_id": "user_1", "amount": -10, "currency": "RUB"},
        )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_create_order_invalid_currency(self, client):
        """currency 'rubles' не соответствует pattern ^[A-Z]{3}$ → 422."""
        response = await client.post(
            "/api/v1/orders",
            json={"user_id": "user_1", "amount": 100, "currency": "rubles"},
        )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_create_order_missing_user_id(self, client):
        """Отсутствие обязательного поля user_id → 422."""
        response = await client.post(
            "/api/v1/orders",
            json={"amount": 100},
        )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_get_order(self, client):
        response = await client.get("/api/v1/orders/ORD-123")
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "ORD-123"
        assert data["status"] == "created"
        assert data["total"] == 1500.0


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Exception handlers
# ═════════════════════════════════════════════════════════════════════════════


class TestExceptionHandlers:
    """Тесты обработки ошибок ActionMachine."""

    @pytest.fixture
    async def error_client(self, machine):
        """Клиент с эндпоинтами, бросающими ошибки."""
        adapter = FastApiAdapter(machine=machine, title="Error API")
        adapter.post("/auth-error", AuthErrorAction)
        adapter.post("/validation-error", ValidationErrorAction)
        adapter.post("/internal-error", InternalErrorAction)
        app = adapter.build()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.anyio
    async def test_authorization_error_returns_403(self, error_client):
        """AuthorizationError → 403 Forbidden."""
        response = await error_client.post("/auth-error", json={})
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data

    @pytest.mark.anyio
    async def test_validation_field_error_returns_422(self, error_client):
        """ValidationFieldError → 422 Unprocessable Entity."""
        response = await error_client.post("/validation-error", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "amount" in data["detail"]

    @pytest.mark.anyio
    async def test_generic_error_returns_500(self, error_client):
        """Необработанное исключение → 500 Internal Server Error."""
        response = await error_client.post("/internal-error", json={})
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Internal server error"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Маппинг (params_mapper, response_mapper)
# ═════════════════════════════════════════════════════════════════════════════


class TestMapping:
    """Тесты маппинга между протокольными моделями и типами действия."""

    @pytest.fixture
    async def mapping_client(self, machine):
        """Клиент с маршрутами, использующими мапперы."""

        def params_mapper(alt: AltRequest) -> OrderParams:
            return OrderParams(user_id=alt.raw_data, amount=999.0, currency="USD")

        def response_mapper(res: OrderResult) -> AltResponse:
            return AltResponse(transformed=f"{res.order_id}:{res.status}")

        adapter = FastApiAdapter(machine=machine, title="Mapping API")

        # Только params_mapper
        adapter.post(
            "/with-params-mapper",
            MappableAction,
            request_model=AltRequest,
            params_mapper=params_mapper,
        )

        # Оба маппера
        adapter.post(
            "/with-both-mappers",
            MappableAction,
            request_model=AltRequest,
            response_model=AltResponse,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
        )

        app = adapter.build()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.anyio
    async def test_params_mapper_transforms_request(self, mapping_client):
        """params_mapper преобразует AltRequest в OrderParams."""
        response = await mapping_client.post(
            "/with-params-mapper",
            json={"raw_data": "mapper_user"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "ORD-mapper_user"
        assert data["total"] == 999.0

    @pytest.mark.anyio
    async def test_response_mapper_transforms_response(self, mapping_client):
        """response_mapper преобразует OrderResult в AltResponse."""
        response = await mapping_client.post(
            "/with-both-mappers",
            json={"raw_data": "both_user"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["transformed"] == "ORD-both_user:mapped"
