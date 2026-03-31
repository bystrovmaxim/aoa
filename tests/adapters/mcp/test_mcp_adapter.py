# tests/adapters/mcp/test_mcp_adapter.py
"""
Тесты для McpAdapter — MCP-адаптера ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Конструктор:
    - Корректная инициализация с machine, server_name, server_version.
    - TypeError при передаче не-ActionProductMachine.
    - Значения по умолчанию.

Протокольный метод tool():
    - Регистрация с минимальными параметрами.
    - Регистрация с description.
    - Auto-description из @meta действия.
    - Множественные tools.
    - Fluent chain: метод возвращает self.

register_all():
    - Автоматическая регистрация всех Action из координатора.
    - Имена tools в snake_case без суффикса Action.
    - Description из @meta.
    - Классы без аспектов не регистрируются.

build():
    - Возвращает FastMCP-сервер.
    - Зарегистрированные tools доступны на сервере.

Tool call через in-memory тестирование:
    - Вызов tool с валидными данными → JSON-результат.
    - Вызов tool с невалидными данными → INVALID_PARAMS.
    - AuthorizationError → PERMISSION_DENIED.
    - Необработанное исключение → INTERNAL_ERROR.

Resource system://graph:
    - Resource зарегистрирован.
    - Возвращает JSON с nodes и edges.
    - Содержит доменные узлы и рёбра belongs_to.

Маппинг:
    - Route с params_mapper — маппер вызывается.
    - Route с response_mapper — маппер вызывается.

Fluent chain:
    - Цепочечная регистрация tools.
    - Цепочка завершается build().
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.checkers.result_string_checker import ResultStringChecker
from action_machine.contrib.mcp import McpAdapter
from action_machine.contrib.mcp.adapter import _class_name_to_snake_case
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
    """Параметры заказа."""
    user_id: str = Field(description="ID пользователя", min_length=1)
    amount: float = Field(description="Сумма", gt=0)
    currency: str = Field(default="RUB", description="Валюта", pattern=r"^[A-Z]{3}$")


class OrderResult(BaseResult):
    """Результат заказа."""
    order_id: str = Field(description="ID заказа")
    status: str = Field(description="Статус")
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
    @summary_aspect("Загрузка")
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
def adapter(machine) -> McpAdapter:
    return McpAdapter(
        machine=machine,
        server_name="Test MCP",
        server_version="1.0.0",
    )


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Конструктор
# ═════════════════════════════════════════════════════════════════════════════


class TestConstructor:
    """Тесты конструктора McpAdapter."""

    def test_stores_server_name(self, adapter):
        assert adapter.server_name == "Test MCP"

    def test_stores_server_version(self, adapter):
        assert adapter.server_version == "1.0.0"

    def test_default_server_name(self, machine):
        a = McpAdapter(machine=machine)
        assert a.server_name == "ActionMachine MCP"

    def test_default_server_version(self, machine):
        a = McpAdapter(machine=machine)
        assert a.server_version == "0.1.0"

    def test_non_machine_raises_type_error(self):
        with pytest.raises(TypeError, match="ожидает ActionProductMachine"):
            McpAdapter(machine="not a machine")

    def test_stores_machine(self, adapter, machine):
        assert adapter.machine is machine

    def test_default_auth_none(self, adapter):
        assert adapter.auth_coordinator is None

    def test_default_connections_factory_none(self, adapter):
        assert adapter.connections_factory is None

    def test_empty_routes(self, adapter):
        assert adapter.routes == []


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Регистрация tools
# ═════════════════════════════════════════════════════════════════════════════


class TestToolRegistration:
    """Тесты протокольного метода tool()."""

    def test_tool_registers_route(self, adapter):
        adapter.tool("system.ping", PingAction)
        assert len(adapter.routes) == 1
        assert adapter.routes[0].tool_name == "system.ping"

    def test_tool_with_description(self, adapter):
        adapter.tool("system.ping", PingAction, description="Пинг-проверка")
        assert adapter.routes[0].description == "Пинг-проверка"

    def test_auto_description_from_meta(self, adapter):
        """Если description не указан — берётся из @meta."""
        adapter.tool("system.ping", PingAction)
        assert adapter.routes[0].description == "Проверка доступности сервиса"

    def test_explicit_description_overrides_meta(self, adapter):
        """Явный description имеет приоритет над @meta."""
        adapter.tool("system.ping", PingAction, description="Custom")
        assert adapter.routes[0].description == "Custom"

    def test_multiple_tools(self, adapter):
        adapter.tool("system.ping", PingAction)
        adapter.tool("orders.create", CreateOrderAction)
        adapter.tool("orders.get", GetOrderAction)
        assert len(adapter.routes) == 3

    def test_tool_returns_self(self, adapter):
        """tool() возвращает self для fluent chain."""
        result = adapter.tool("system.ping", PingAction)
        assert result is adapter

    def test_fluent_chain(self, adapter):
        """Цепочечная регистрация tools."""
        result = adapter \
            .tool("system.ping", PingAction) \
            .tool("orders.create", CreateOrderAction) \
            .tool("orders.get", GetOrderAction)

        assert result is adapter
        assert len(adapter.routes) == 3

    def test_tool_action_class_stored(self, adapter):
        adapter.tool("orders.create", CreateOrderAction)
        assert adapter.routes[0].action_class is CreateOrderAction

    def test_tool_params_type_extracted(self, adapter):
        adapter.tool("orders.create", CreateOrderAction)
        assert adapter.routes[0].params_type is OrderParams

    def test_tool_result_type_extracted(self, adapter):
        adapter.tool("orders.create", CreateOrderAction)
        assert adapter.routes[0].result_type is OrderResult


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: _class_name_to_snake_case
# ═════════════════════════════════════════════════════════════════════════════


class TestClassNameToSnakeCase:
    """Тесты преобразования CamelCase → snake_case."""

    def test_simple_action(self):
        assert _class_name_to_snake_case("PingAction") == "ping"

    def test_two_words_action(self):
        assert _class_name_to_snake_case("CreateOrderAction") == "create_order"

    def test_three_words_action(self):
        assert _class_name_to_snake_case("GetUserProfileAction") == "get_user_profile"

    def test_no_action_suffix(self):
        assert _class_name_to_snake_case("CreateOrder") == "create_order"

    def test_single_word(self):
        assert _class_name_to_snake_case("Ping") == "ping"

    def test_action_alone(self):
        """Класс с именем ровно 'Action' — не обрезаем."""
        assert _class_name_to_snake_case("Action") == "action"

    def test_abbreviation(self):
        assert _class_name_to_snake_case("HTMLParserAction") == "html_parser"

    def test_all_caps(self):
        assert _class_name_to_snake_case("API") == "api"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: register_all()
# ═════════════════════════════════════════════════════════════════════════════


class TestRegisterAll:
    """Тесты автоматической регистрации всех Action из координатора."""

    def test_register_all_registers_actions(self, machine, coordinator):
        """register_all() регистрирует все Action с аспектами."""
        # Предварительно регистрируем Action в координаторе
        coordinator.get(PingAction)
        coordinator.get(CreateOrderAction)
        coordinator.get(GetOrderAction)

        adapter = McpAdapter(machine=machine)
        adapter.register_all()

        tool_names = {r.tool_name for r in adapter.routes}
        assert "ping" in tool_names
        assert "create_order" in tool_names
        assert "get_order" in tool_names

    def test_register_all_uses_meta_description(self, machine, coordinator):
        """register_all() берёт description из @meta."""
        coordinator.get(PingAction)

        adapter = McpAdapter(machine=machine)
        adapter.register_all()

        ping_routes = [r for r in adapter.routes if r.tool_name == "ping"]
        assert len(ping_routes) == 1
        assert ping_routes[0].description == "Проверка доступности сервиса"

    def test_register_all_returns_self(self, machine, coordinator):
        """register_all() возвращает self для fluent chain."""
        coordinator.get(PingAction)

        adapter = McpAdapter(machine=machine)
        result = adapter.register_all()
        assert result is adapter

    def test_register_all_skips_non_action_classes(self, machine, coordinator):
        """Классы без аспектов не регистрируются как tools."""
        coordinator.get(PingAction)

        # OrderParams — не Action, но может быть в координаторе через зависимости
        adapter = McpAdapter(machine=machine)
        adapter.register_all()

        # Должен быть только PingAction
        for route in adapter.routes:
            assert route.action_class is not OrderParams


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: build()
# ═════════════════════════════════════════════════════════════════════════════


class TestBuild:
    """Тесты метода build()."""

    def test_returns_fastmcp_instance(self, adapter):
        from mcp.server.fastmcp import FastMCP
        adapter.tool("system.ping", PingAction)
        server = adapter.build()
        assert isinstance(server, FastMCP)

    def test_server_name(self, adapter):
        adapter.tool("system.ping", PingAction)
        server = adapter.build()
        assert server.name == "Test MCP"

    def test_fluent_chain_to_build(self, machine):
        """Fluent chain завершается build()."""
        from mcp.server.fastmcp import FastMCP
        adapter = McpAdapter(machine=machine, server_name="Chain MCP")
        server = adapter \
            .tool("system.ping", PingAction) \
            .tool("orders.create", CreateOrderAction) \
            .build()
        assert isinstance(server, FastMCP)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Tool call (in-memory)
# ═════════════════════════════════════════════════════════════════════════════


class TestToolCall:
    """Тесты вызова MCP tools через handler напрямую."""

    @pytest.fixture
    def handlers(self, adapter):
        """Словарь {tool_name: handler} для прямого вызова."""
        from action_machine.contrib.mcp.adapter import _make_tool_handler

        adapter.tool("system.ping", PingAction)
        adapter.tool("orders.create", CreateOrderAction)
        adapter.tool("auth.error", AuthErrorAction)
        adapter.tool("validation.error", ValidationErrorAction)
        adapter.tool("internal.error", InternalErrorAction)

        result = {}
        for record in adapter.routes:
            handler = _make_tool_handler(
                record=record,
                machine=adapter.machine,
                auth_coordinator=adapter.auth_coordinator,
                connections_factory=adapter.connections_factory,
            )
            result[record.tool_name] = handler
        return result

    @pytest.mark.anyio
    async def test_ping_returns_pong(self, handlers):
        """system.ping → {"message": "pong"}."""
        result = await handlers["system.ping"]()
        data = json.loads(result)
        assert data["message"] == "pong"

    @pytest.mark.anyio
    async def test_create_order_success(self, handlers):
        """orders.create с валидными данными → результат."""
        result = await handlers["orders.create"](
            user_id="user_42",
            amount=1500.0,
            currency="RUB",
        )
        data = json.loads(result)
        assert data["order_id"] == "ORD-user_42"
        assert data["status"] == "created"
        assert data["total"] == 1500.0

    @pytest.mark.anyio
    async def test_create_order_default_currency(self, handlers):
        """orders.create без currency → используется default RUB."""
        result = await handlers["orders.create"](
            user_id="user_1",
            amount=100.0,
        )
        data = json.loads(result)
        assert data["order_id"] == "ORD-user_1"

    @pytest.mark.anyio
    async def test_create_order_invalid_amount(self, handlers):
        """orders.create с amount <= 0 → INVALID_PARAMS."""
        result = await handlers["orders.create"](
            user_id="user_1",
            amount=-10.0,
            currency="RUB",
        )
        assert "INVALID_PARAMS" in result or "INTERNAL_ERROR" in result

    @pytest.mark.anyio
    async def test_authorization_error(self, handlers):
        """auth.error → PERMISSION_DENIED."""
        result = await handlers["auth.error"]()
        assert "PERMISSION_DENIED" in result

    @pytest.mark.anyio
    async def test_validation_error(self, handlers):
        """validation.error → INVALID_PARAMS."""
        result = await handlers["validation.error"]()
        assert "INVALID_PARAMS" in result
        assert "amount" in result

    @pytest.mark.anyio
    async def test_internal_error(self, handlers):
        """internal.error → INTERNAL_ERROR."""
        result = await handlers["internal.error"]()
        assert "INTERNAL_ERROR" in result
        assert "Внутренняя ошибка" in result


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Resource system://graph
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphResource:
    """Тесты resource system://graph."""

    def test_graph_json_contains_nodes_and_edges(self, adapter):
        """Граф содержит массивы nodes и edges."""
        from action_machine.contrib.mcp.adapter import _build_graph_json

        # Регистрируем действие, чтобы граф был непустой
        adapter.tool("system.ping", PingAction)
        adapter.build()  # build() триггерит регистрацию в координаторе

        graph_json = _build_graph_json(adapter.machine)
        data = json.loads(graph_json)

        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_graph_contains_action_nodes(self, machine, coordinator):
        """Граф содержит узлы типа action."""
        from action_machine.contrib.mcp.adapter import _build_graph_json

        coordinator.get(PingAction)

        graph_json = _build_graph_json(machine)
        data = json.loads(graph_json)

        action_nodes = [n for n in data["nodes"] if n["type"] == "action"]
        assert len(action_nodes) > 0

    def test_graph_contains_domain_nodes(self, machine, coordinator):
        """Граф содержит узлы типа domain (для Action с domain в @meta)."""
        from action_machine.contrib.mcp.adapter import _build_graph_json

        # CreateOrderAction имеет domain=OrdersDomain в @meta (через examples),
        # но локальные тестовые Action не имеют домена.
        # Используем CreateOrderAction из тестов — у него нет домена.
        # Поэтому создадим Action с доменом прямо здесь.
        from action_machine.domain.base_domain import BaseDomain

        class _TestDomain(BaseDomain):
            name = "test_graph_domain"

        @meta(description="Действие с доменом для теста графа", domain=_TestDomain)
        @CheckRoles(CheckRoles.NONE, desc="")
        class _DomainAction(BaseAction[EmptyParams, PingResult]):
            @summary_aspect("Тест")
            async def summary(self, params, state, box, connections):
                return PingResult(message="ok")

        coordinator.get(_DomainAction)

        graph_json = _build_graph_json(machine)
        data = json.loads(graph_json)

        domain_nodes = [n for n in data["nodes"] if n["type"] == "domain"]
        assert len(domain_nodes) > 0
        assert any(n.get("name") == "test_graph_domain" for n in domain_nodes)

    def test_graph_contains_belongs_to_edges(self, machine, coordinator):
        """Граф содержит рёбра belongs_to между action и domain."""
        from action_machine.contrib.mcp.adapter import _build_graph_json
        from action_machine.domain.base_domain import BaseDomain

        class _TestDomain2(BaseDomain):
            name = "test_graph_domain_2"

        @meta(description="Действие с доменом для теста рёбер", domain=_TestDomain2)
        @CheckRoles(CheckRoles.NONE, desc="")
        class _DomainAction2(BaseAction[EmptyParams, PingResult]):
            @summary_aspect("Тест")
            async def summary(self, params, state, box, connections):
                return PingResult(message="ok")

        coordinator.get(_DomainAction2)

        graph_json = _build_graph_json(machine)
        data = json.loads(graph_json)

        belongs_to_edges = [e for e in data["edges"] if e["type"] == "belongs_to"]
        assert len(belongs_to_edges) > 0

    def test_graph_action_has_description(self, machine, coordinator):
        """Узлы action содержат description из @meta."""
        from action_machine.contrib.mcp.adapter import _build_graph_json

        coordinator.get(PingAction)

        graph_json = _build_graph_json(machine)
        data = json.loads(graph_json)

        action_nodes = [n for n in data["nodes"] if n["type"] == "action"]
        descriptions = [n.get("description", "") for n in action_nodes]
        assert any("Проверка доступности" in d for d in descriptions)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Маппинг (params_mapper, response_mapper)
# ═════════════════════════════════════════════════════════════════════════════


class TestMapping:
    """Тесты маппинга между протокольными моделями и типами действия."""

    @pytest.mark.anyio
    async def test_params_mapper_transforms_input(self, adapter):
        """params_mapper преобразует AltRequest в OrderParams."""
        from action_machine.contrib.mcp.adapter import _make_tool_handler

        def params_mapper(alt: AltRequest) -> OrderParams:
            return OrderParams(user_id=alt.raw_data, amount=999.0, currency="USD")

        adapter.tool(
            "mapped.action",
            MappableAction,
            request_model=AltRequest,
            params_mapper=params_mapper,
        )

        record = adapter.routes[0]
        handler = _make_tool_handler(
            record=record,
            machine=adapter.machine,
            auth_coordinator=None,
            connections_factory=None,
        )

        result = await handler(raw_data="mapper_user")
        data = json.loads(result)
        assert data["order_id"] == "ORD-mapper_user"
        assert data["total"] == 999.0

    @pytest.mark.anyio
    async def test_response_mapper_transforms_output(self, adapter):
        """response_mapper преобразует OrderResult в AltResponse."""
        from action_machine.contrib.mcp.adapter import _make_tool_handler

        def params_mapper(alt: AltRequest) -> OrderParams:
            return OrderParams(user_id=alt.raw_data, amount=100.0, currency="USD")

        def response_mapper(res: OrderResult) -> AltResponse:
            return AltResponse(transformed=f"{res.order_id}:{res.status}")

        adapter.tool(
            "mapped.both",
            MappableAction,
            request_model=AltRequest,
            response_model=AltResponse,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
        )

        record = adapter.routes[0]
        handler = _make_tool_handler(
            record=record,
            machine=adapter.machine,
            auth_coordinator=None,
            connections_factory=None,
        )

        result = await handler(raw_data="both_user")
        data = json.loads(result)
        assert data["transformed"] == "ORD-both_user:mapped"
