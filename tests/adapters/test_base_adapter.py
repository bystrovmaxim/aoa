# tests/adapters/test_base_adapter.py
"""
Тесты для базовой инфраструктуры адаптеров ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

BaseAdapter:
    - Конструктор: корректная инициализация с machine, auth_coordinator,
      connections_factory.
    - Конструктор: TypeError при передаче не-ActionProductMachine.
    - Конструктор: значения по умолчанию (auth=None, connections=None).
    - _add_route(): добавляет RouteRecord в _routes и возвращает self.
    - routes: свойство возвращает список зарегистрированных маршрутов.
    - build(): вызывается и возвращает протокольное приложение.
    - Fluent chain: протокольные методы возвращают self.

BaseRouteRecord:
    - Нельзя инстанцировать напрямую (TypeError).
    - Автоизвлечение params_type и result_type из action_class.
    - Вычисляемые свойства: params_type, result_type,
      effective_request_model, effective_response_model.
    - Frozen: попытка изменения поля → FrozenInstanceError.
    - Значения по умолчанию: request_model=None, response_model=None,
      params_mapper=None, response_mapper=None.
    - Валидация: params_mapper обязателен если request_model != params_type.
    - Валидация: response_mapper обязателен если response_model != result_type.
    - Валидация: маппер при совпадающих типах допустим.
    - Протокольно-специфичные поля в наследнике типизированы.

extract_action_types:
    - Извлекает P и R из BaseAction[P, R].
    - TypeError если generic-параметры не указаны.

Интеграция:
    - Полный цикл: создание адаптера → регистрация маршрутов → build().
    - Минимальная регистрация (только action_class).
    - Регистрация с request_model и маппером.
    - Регистрация с обоими моделями и обоими мапперами.
    - Fluent chain: цепочечная регистрация маршрутов.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import Field

from action_machine.adapters.base_adapter import BaseAdapter
from action_machine.adapters.base_route_record import BaseRouteRecord, extract_action_types
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели данных
# ═════════════════════════════════════════════════════════════════════════════


class MockParams(BaseParams):
    """Параметры действия для тестов."""
    pass


class MockResult(BaseResult):
    """Результат действия для тестов."""
    pass


class OrderParams(BaseParams):
    """Параметры заказа — отличаются от протокольной модели запроса."""
    user_id: str = Field(description="ID пользователя")
    amount: float = Field(description="Сумма заказа")


class OrderResult(BaseResult):
    """Результат заказа — отличается от протокольной модели ответа."""
    order_id: str = Field(description="ID заказа")
    status: str = Field(description="Статус")


class ListOrdersRequest(BaseParams):
    """Протокольная модель запроса списка (отличается от OrderParams)."""
    page: int = Field(default=1, description="Номер страницы")
    limit: int = Field(default=10, description="Размер страницы")


class ListOrdersResponse(BaseResult):
    """Протокольная модель ответа списка (отличается от OrderResult)."""
    order_items: list = Field(default_factory=list, description="Элементы списка")
    total: int = Field(default=0, description="Всего")


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые функции-мапперы
# ═════════════════════════════════════════════════════════════════════════════


def map_list_request_to_params(req: Any) -> OrderParams:
    """Преобразует ListOrdersRequest в OrderParams."""
    return OrderParams(user_id="system", amount=0.0)


def map_order_result_to_list_response(res: Any) -> ListOrdersResponse:
    """Преобразует OrderResult в ListOrdersResponse."""
    return ListOrdersResponse(order_items=[], total=0)


def identity_mapper(x: Any) -> Any:
    """Маппер-тождество для тестов."""
    return x


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые действия
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Создание заказа")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    """Действие создания заказа."""

    @summary_aspect("Создание")
    async def summary(
        self, params: OrderParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> OrderResult:
        return OrderResult(order_id="ORD-1", status="created")


@meta(description="Список заказов")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class ListOrdersAction(BaseAction[OrderParams, OrderResult]):
    """Действие получения списка заказов."""

    @summary_aspect("Список")
    async def summary(
        self, params: OrderParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> OrderResult:
        return OrderResult(order_id="ORD-1", status="ok")


@meta(description="Действие с пустыми типами")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class SimpleAction(BaseAction[MockParams, MockResult]):
    """Действие с MockParams/MockResult."""

    @summary_aspect("Простое")
    async def summary(
        self, params: MockParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> MockResult:
        return MockResult()


class NotAnAction:
    """Класс, не наследующий BaseAction."""
    pass


class BareAction(BaseAction):
    """Действие без generic-параметров — для теста TypeError."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Конкретный RouteRecord для тестов
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MockRouteRecord(BaseRouteRecord):
    """Конкретный RouteRecord с HTTP-специфичными полями."""
    method: str = "GET"
    path: str = "/"
    tags: tuple[str, ...] = ()
    summary: str = ""


# ═════════════════════════════════════════════════════════════════════════════
# Mock-адаптер для тестов
# ═════════════════════════════════════════════════════════════════════════════


class MockAdapter(BaseAdapter[MockRouteRecord]):
    """
    Mock-адаптер для тестирования BaseAdapter.

    Предоставляет протокольные методы post() и get(), имитирующие
    API реального HTTP-адаптера. Каждый метод создаёт MockRouteRecord,
    добавляет его через _add_route() и возвращает self для fluent chain.
    """

    def post(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Any = None,
        response_mapper: Any = None,
        tags: list[str] | None = None,
        summary: str = "",
    ) -> MockAdapter:
        """Регистрирует POST-маршрут. Возвращает self для fluent chain."""
        record = MockRouteRecord(
            action_class=action_class,
            request_model=request_model,
            response_model=response_model,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
            method="POST",
            path=path,
            tags=tuple(tags or ()),
            summary=summary,
        )
        return self._add_route(record)

    def get(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Any = None,
        response_mapper: Any = None,
        tags: list[str] | None = None,
        summary: str = "",
    ) -> MockAdapter:
        """Регистрирует GET-маршрут. Возвращает self для fluent chain."""
        record = MockRouteRecord(
            action_class=action_class,
            request_model=request_model,
            response_model=response_model,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
            method="GET",
            path=path,
            tags=tuple(tags or ()),
            summary=summary,
        )
        return self._add_route(record)

    def build(self) -> dict[str, Any]:
        """Создаёт mock-приложение — словарь с маршрутами."""
        return {
            "routes": list(self._routes),
            "route_count": len(self._routes),
        }


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def machine() -> ActionProductMachine:
    """ActionProductMachine с mock-логгером."""
    return ActionProductMachine(mode="test", log_coordinator=AsyncMock())


@pytest.fixture
def adapter(machine: ActionProductMachine) -> MockAdapter:
    """MockAdapter без аутентификации и соединений."""
    return MockAdapter(machine=machine)


@pytest.fixture
def adapter_with_auth(machine: ActionProductMachine) -> MockAdapter:
    """MockAdapter с mock-координатором аутентификации."""
    return MockAdapter(machine=machine, auth_coordinator=MagicMock())


@pytest.fixture
def adapter_with_connections(machine: ActionProductMachine) -> MockAdapter:
    """MockAdapter с фабрикой соединений."""
    return MockAdapter(
        machine=machine,
        connections_factory=MagicMock(return_value={"db": MagicMock(spec=BaseResourceManager)}),
    )


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: extract_action_types
# ═════════════════════════════════════════════════════════════════════════════


class TestExtractActionTypes:
    """Тесты функции extract_action_types."""

    def test_extracts_params_and_result(self):
        """Извлекает P и R из BaseAction[OrderParams, OrderResult]."""
        p, r = extract_action_types(CreateOrderAction)
        assert p is OrderParams
        assert r is OrderResult

    def test_extracts_mock_types(self):
        """Извлекает P и R из BaseAction[MockParams, MockResult]."""
        p, r = extract_action_types(SimpleAction)
        assert p is MockParams
        assert r is MockResult

    def test_bare_action_raises_type_error(self):
        """BaseAction без generic-параметров → TypeError."""
        with pytest.raises(TypeError, match="Не удалось извлечь generic-параметры"):
            extract_action_types(BareAction)

    def test_not_action_raises_type_error(self):
        """Класс, не наследующий BaseAction → TypeError."""
        with pytest.raises(TypeError, match="Не удалось извлечь generic-параметры"):
            extract_action_types(NotAnAction)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Конструктор BaseAdapter
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseAdapterConstructor:
    """Тесты конструктора BaseAdapter через MockAdapter."""

    def test_stores_machine(self, adapter: MockAdapter, machine: ActionProductMachine):
        """Конструктор сохраняет machine."""
        assert adapter.machine is machine

    def test_stores_auth_coordinator(self, adapter_with_auth: MockAdapter):
        """Конструктор сохраняет auth_coordinator."""
        assert adapter_with_auth.auth_coordinator is not None

    def test_stores_connections_factory(self, adapter_with_connections: MockAdapter):
        """Конструктор сохраняет connections_factory."""
        assert adapter_with_connections.connections_factory is not None

    def test_default_auth_none(self, adapter: MockAdapter):
        """По умолчанию auth_coordinator = None."""
        assert adapter.auth_coordinator is None

    def test_default_connections_factory_none(self, adapter: MockAdapter):
        """По умолчанию connections_factory = None."""
        assert adapter.connections_factory is None

    def test_empty_routes(self, adapter: MockAdapter):
        """Начальный список маршрутов пуст."""
        assert adapter.routes == []

    def test_non_machine_raises_type_error(self):
        """TypeError при передаче не-ActionProductMachine."""
        with pytest.raises(TypeError, match="ожидает ActionProductMachine"):
            MockAdapter(machine="not a machine")

    def test_none_machine_raises_type_error(self):
        """TypeError при передаче None."""
        with pytest.raises(TypeError, match="ожидает ActionProductMachine"):
            MockAdapter(machine=None)

    def test_int_machine_raises_type_error(self):
        """TypeError при передаче числа."""
        with pytest.raises(TypeError, match="ожидает ActionProductMachine"):
            MockAdapter(machine=42)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: BaseRouteRecord
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseRouteRecord:
    """Тесты BaseRouteRecord через конкретный MockRouteRecord."""

    def test_cannot_instantiate_base_directly(self):
        """BaseRouteRecord нельзя инстанцировать напрямую → TypeError."""
        with pytest.raises(TypeError, match="нельзя инстанцировать напрямую"):
            BaseRouteRecord(action_class=CreateOrderAction)

    def test_auto_extracts_params_type(self):
        """params_type извлекается автоматически из action_class."""
        record = MockRouteRecord(action_class=CreateOrderAction)
        assert record.params_type is OrderParams

    def test_auto_extracts_result_type(self):
        """result_type извлекается автоматически из action_class."""
        record = MockRouteRecord(action_class=CreateOrderAction)
        assert record.result_type is OrderResult

    def test_effective_request_model_default(self):
        """effective_request_model = params_type когда request_model=None."""
        record = MockRouteRecord(action_class=CreateOrderAction)
        assert record.effective_request_model is OrderParams

    def test_effective_request_model_custom(self):
        """effective_request_model = request_model когда он указан."""
        record = MockRouteRecord(
            action_class=CreateOrderAction,
            request_model=ListOrdersRequest,
            params_mapper=map_list_request_to_params,
        )
        assert record.effective_request_model is ListOrdersRequest

    def test_effective_response_model_default(self):
        """effective_response_model = result_type когда response_model=None."""
        record = MockRouteRecord(action_class=CreateOrderAction)
        assert record.effective_response_model is OrderResult

    def test_effective_response_model_custom(self):
        """effective_response_model = response_model когда он указан."""
        record = MockRouteRecord(
            action_class=CreateOrderAction,
            response_model=ListOrdersResponse,
            response_mapper=map_order_result_to_list_response,
        )
        assert record.effective_response_model is ListOrdersResponse

    def test_minimal_creation(self):
        """Минимальное создание — только action_class."""
        record = MockRouteRecord(action_class=CreateOrderAction)
        assert record.action_class is CreateOrderAction
        assert record.request_model is None
        assert record.response_model is None
        assert record.params_mapper is None
        assert record.response_mapper is None

    def test_frozen_prevents_modification(self):
        """Frozen: попытка изменения поля → FrozenInstanceError."""
        record = MockRouteRecord(action_class=CreateOrderAction)
        with pytest.raises(FrozenInstanceError):
            record.action_class = SimpleAction

    def test_frozen_prevents_path_modification(self):
        """Frozen: попытка изменения протокольного поля → FrozenInstanceError."""
        record = MockRouteRecord(action_class=CreateOrderAction, path="/original")
        with pytest.raises(FrozenInstanceError):
            record.path = "/modified"

    def test_protocol_specific_fields_defaults(self):
        """Протокольно-специфичные поля имеют дефолты."""
        record = MockRouteRecord(action_class=CreateOrderAction)
        assert record.method == "GET"
        assert record.path == "/"
        assert record.tags == ()
        assert record.summary == ""

    def test_protocol_specific_fields_custom(self):
        """Протокольно-специфичные поля принимают значения."""
        record = MockRouteRecord(
            action_class=CreateOrderAction,
            method="POST",
            path="/api/v1/orders",
            tags=("orders", "create"),
            summary="Создание заказа",
        )
        assert record.method == "POST"
        assert record.path == "/api/v1/orders"
        assert record.tags == ("orders", "create")
        assert record.summary == "Создание заказа"

    def test_not_base_action_raises_type_error(self):
        """action_class не BaseAction → TypeError."""
        with pytest.raises(TypeError, match="подклассом BaseAction"):
            MockRouteRecord(action_class=NotAnAction)

    def test_bare_action_raises_type_error(self):
        """BaseAction без generic-параметров → TypeError."""
        with pytest.raises(TypeError, match="Не удалось извлечь generic-параметры"):
            MockRouteRecord(action_class=BareAction)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Валидация инвариантов маппинга
# ═════════════════════════════════════════════════════════════════════════════


class TestRouteRecordMapperValidation:
    """Тесты валидации params_mapper и response_mapper."""

    def test_different_request_model_without_mapper_raises(self):
        """request_model != params_type и params_mapper=None → ValueError."""
        with pytest.raises(ValueError, match="params_mapper не указан"):
            MockRouteRecord(
                action_class=CreateOrderAction,
                request_model=ListOrdersRequest,
            )

    def test_different_response_model_without_mapper_raises(self):
        """response_model != result_type и response_mapper=None → ValueError."""
        with pytest.raises(ValueError, match="response_mapper не указан"):
            MockRouteRecord(
                action_class=CreateOrderAction,
                response_model=ListOrdersResponse,
            )

    def test_both_different_without_mappers_raises(self):
        """Оба отличаются, оба маппера отсутствуют → ValueError (params первый)."""
        with pytest.raises(ValueError, match="params_mapper не указан"):
            MockRouteRecord(
                action_class=CreateOrderAction,
                request_model=ListOrdersRequest,
                response_model=ListOrdersResponse,
            )

    def test_no_request_model_no_mapper_ok(self):
        """request_model=None → params_mapper не нужен."""
        record = MockRouteRecord(action_class=CreateOrderAction)
        assert record.params_mapper is None

    def test_no_response_model_no_mapper_ok(self):
        """response_model=None → response_mapper не нужен."""
        record = MockRouteRecord(action_class=CreateOrderAction)
        assert record.response_mapper is None

    def test_same_request_model_no_mapper_ok(self):
        """request_model == params_type → маппер не нужен."""
        record = MockRouteRecord(
            action_class=CreateOrderAction,
            request_model=OrderParams,
        )
        assert record.params_mapper is None

    def test_same_response_model_no_mapper_ok(self):
        """response_model == result_type → маппер не нужен."""
        record = MockRouteRecord(
            action_class=CreateOrderAction,
            response_model=OrderResult,
        )
        assert record.response_mapper is None

    def test_same_types_with_mappers_ok(self):
        """Маппер при совпадающих типах допустим."""
        record = MockRouteRecord(
            action_class=CreateOrderAction,
            request_model=OrderParams,
            response_model=OrderResult,
            params_mapper=identity_mapper,
            response_mapper=identity_mapper,
        )
        assert record.params_mapper is identity_mapper
        assert record.response_mapper is identity_mapper

    def test_different_request_with_mapper_ok(self):
        """request_model != params_type с маппером → OK."""
        record = MockRouteRecord(
            action_class=CreateOrderAction,
            request_model=ListOrdersRequest,
            params_mapper=map_list_request_to_params,
        )
        assert record.params_mapper is map_list_request_to_params

    def test_different_response_with_mapper_ok(self):
        """response_model != result_type с маппером → OK."""
        record = MockRouteRecord(
            action_class=CreateOrderAction,
            response_model=ListOrdersResponse,
            response_mapper=map_order_result_to_list_response,
        )
        assert record.response_mapper is map_order_result_to_list_response


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Протокольные методы адаптера (post, get)
# ═════════════════════════════════════════════════════════════════════════════


class TestAdapterProtocolMethods:
    """Тесты протокольных методов MockAdapter."""

    def test_post_minimal(self, adapter: MockAdapter):
        """post() с минимальными аргументами."""
        adapter.post("/orders", CreateOrderAction)

        assert len(adapter.routes) == 1
        record = adapter.routes[0]
        assert record.action_class is CreateOrderAction
        assert record.method == "POST"
        assert record.path == "/orders"
        assert record.params_type is OrderParams
        assert record.result_type is OrderResult
        assert record.request_model is None
        assert record.response_model is None
        assert record.params_mapper is None
        assert record.response_mapper is None

    def test_get_minimal(self, adapter: MockAdapter):
        """get() с минимальными аргументами."""
        adapter.get("/orders", ListOrdersAction)

        assert len(adapter.routes) == 1
        record = adapter.routes[0]
        assert record.method == "GET"
        assert record.path == "/orders"

    def test_post_with_request_model_and_mapper(self, adapter: MockAdapter):
        """post() с request_model и params_mapper."""
        adapter.post(
            "/orders/list",
            ListOrdersAction,
            request_model=ListOrdersRequest,
            params_mapper=map_list_request_to_params,
        )

        record = adapter.routes[0]
        assert record.request_model is ListOrdersRequest
        assert record.params_mapper is map_list_request_to_params
        assert record.effective_request_model is ListOrdersRequest

    def test_get_with_both_models_and_mappers(self, adapter: MockAdapter):
        """get() с обоими моделями и обоими мапперами."""
        adapter.get(
            "/orders/{id}",
            CreateOrderAction,
            request_model=ListOrdersRequest,
            response_model=ListOrdersResponse,
            params_mapper=map_list_request_to_params,
            response_mapper=map_order_result_to_list_response,
        )

        record = adapter.routes[0]
        assert record.request_model is ListOrdersRequest
        assert record.response_model is ListOrdersResponse
        assert record.params_mapper is map_list_request_to_params
        assert record.response_mapper is map_order_result_to_list_response

    def test_post_with_tags_and_summary(self, adapter: MockAdapter):
        """post() с tags и summary."""
        adapter.post(
            "/orders",
            CreateOrderAction,
            tags=["orders", "create"],
            summary="Создание заказа",
        )

        record = adapter.routes[0]
        assert record.tags == ("orders", "create")
        assert record.summary == "Создание заказа"

    def test_multiple_routes(self, adapter: MockAdapter):
        """Несколько маршрутов регистрируются независимо."""
        adapter.post("/orders", CreateOrderAction)
        adapter.get("/orders", ListOrdersAction)

        assert len(adapter.routes) == 2
        assert adapter.routes[0].method == "POST"
        assert adapter.routes[0].action_class is CreateOrderAction
        assert adapter.routes[1].method == "GET"
        assert adapter.routes[1].action_class is ListOrdersAction

    def test_post_different_request_without_mapper_raises(self, adapter: MockAdapter):
        """post() с request_model != params_type без маппера → ValueError."""
        with pytest.raises(ValueError, match="params_mapper не указан"):
            adapter.post(
                "/orders",
                CreateOrderAction,
                request_model=ListOrdersRequest,
            )

    def test_fluent_chain_returns_self(self, adapter: MockAdapter):
        """Протокольные методы возвращают self для fluent chain."""
        result = adapter.post("/orders", CreateOrderAction)
        assert result is adapter

    def test_fluent_chain_get_returns_self(self, adapter: MockAdapter):
        """get() возвращает self для fluent chain."""
        result = adapter.get("/ping", SimpleAction)
        assert result is adapter

    def test_fluent_chain_multiple(self, adapter: MockAdapter):
        """Цепочечные вызовы регистрируют все маршруты."""
        result = adapter \
            .post("/orders", CreateOrderAction) \
            .get("/orders", ListOrdersAction) \
            .get("/ping", SimpleAction)

        assert result is adapter
        assert len(adapter.routes) == 3
        assert adapter.routes[0].method == "POST"
        assert adapter.routes[1].method == "GET"
        assert adapter.routes[2].path == "/ping"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: build()
# ═════════════════════════════════════════════════════════════════════════════


class TestBuild:
    """Тесты метода build()."""

    def test_returns_app(self, adapter: MockAdapter):
        """build() возвращает протокольное приложение."""
        adapter.get("/ping", SimpleAction)
        app = adapter.build()
        assert app["route_count"] == 1

    def test_empty_routes(self, adapter: MockAdapter):
        """build() без маршрутов возвращает пустое приложение."""
        app = adapter.build()
        assert app["route_count"] == 0
        assert app["routes"] == []

    def test_preserves_order(self, adapter: MockAdapter):
        """build() сохраняет порядок регистрации."""
        adapter.get("/first", SimpleAction)
        adapter.post("/second", CreateOrderAction)

        app = adapter.build()
        assert app["routes"][0].path == "/first"
        assert app["routes"][1].path == "/second"

    def test_fluent_chain_to_build(self, adapter: MockAdapter):
        """Fluent chain завершается build()."""
        app = adapter \
            .get("/ping", SimpleAction) \
            .post("/orders", CreateOrderAction) \
            .build()

        assert app["route_count"] == 2
        assert app["routes"][0].path == "/ping"
        assert app["routes"][1].path == "/orders"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Интеграция — полный цикл
# ═════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Интеграционные тесты: создание → регистрация → build."""

    def test_full_cycle_minimal(self, adapter: MockAdapter):
        """Полный цикл с минимальной регистрацией."""
        adapter.post("/orders/create", CreateOrderAction)
        adapter.get("/ping", SimpleAction)

        app = adapter.build()
        assert app["route_count"] == 2

        r0 = app["routes"][0]
        assert r0.action_class is CreateOrderAction
        assert r0.method == "POST"
        assert r0.path == "/orders/create"
        assert r0.effective_request_model is OrderParams
        assert r0.effective_response_model is OrderResult

        r1 = app["routes"][1]
        assert r1.action_class is SimpleAction
        assert r1.method == "GET"
        assert r1.effective_request_model is MockParams
        assert r1.effective_response_model is MockResult

    def test_full_cycle_with_mappers(self, adapter: MockAdapter):
        """Полный цикл с различающимися моделями и мапперами."""
        adapter.get(
            "/orders/{id}",
            CreateOrderAction,
            request_model=ListOrdersRequest,
            response_model=ListOrdersResponse,
            params_mapper=map_list_request_to_params,
            response_mapper=map_order_result_to_list_response,
        )

        app = adapter.build()
        record = app["routes"][0]
        assert record.effective_request_model is ListOrdersRequest
        assert record.effective_response_model is ListOrdersResponse
        assert record.params_mapper is map_list_request_to_params
        assert record.response_mapper is map_order_result_to_list_response

    def test_full_cycle_mixed(self, adapter: MockAdapter):
        """Полный цикл: минимальный + с request_model + с обоими."""
        adapter.post("/orders/create", CreateOrderAction)

        adapter.get(
            "/orders/list",
            ListOrdersAction,
            request_model=ListOrdersRequest,
            params_mapper=map_list_request_to_params,
        )

        adapter.get(
            "/orders/{id}",
            CreateOrderAction,
            request_model=ListOrdersRequest,
            response_model=ListOrdersResponse,
            params_mapper=map_list_request_to_params,
            response_mapper=map_order_result_to_list_response,
        )

        app = adapter.build()
        assert app["route_count"] == 3

        # Минимальный — модели совпадают с типами действия
        assert app["routes"][0].effective_request_model is OrderParams
        assert app["routes"][0].effective_response_model is OrderResult
        assert app["routes"][0].params_mapper is None
        assert app["routes"][0].response_mapper is None

        # Только request_model отличается
        assert app["routes"][1].effective_request_model is ListOrdersRequest
        assert app["routes"][1].effective_response_model is OrderResult
        assert app["routes"][1].params_mapper is map_list_request_to_params
        assert app["routes"][1].response_mapper is None

        # Оба отличаются
        assert app["routes"][2].effective_request_model is ListOrdersRequest
        assert app["routes"][2].effective_response_model is ListOrdersResponse
        assert app["routes"][2].params_mapper is map_list_request_to_params
        assert app["routes"][2].response_mapper is map_order_result_to_list_response

    def test_full_cycle_fluent_chain(self, adapter: MockAdapter):
        """Полный цикл через fluent chain."""
        app = adapter \
            .post("/orders/create", CreateOrderAction) \
            .get("/orders/list", ListOrdersAction,
                 request_model=ListOrdersRequest,
                 params_mapper=map_list_request_to_params) \
            .get("/orders/{id}", CreateOrderAction,
                 request_model=ListOrdersRequest,
                 response_model=ListOrdersResponse,
                 params_mapper=map_list_request_to_params,
                 response_mapper=map_order_result_to_list_response) \
            .build()

        assert app["route_count"] == 3

    def test_adapter_with_auth_and_connections(self, machine: ActionProductMachine):
        """Адаптер с auth_coordinator и connections_factory."""
        adapter = MockAdapter(
            machine=machine,
            auth_coordinator=MagicMock(),
            connections_factory=MagicMock(return_value={"db": MagicMock()}),
        )

        assert adapter.auth_coordinator is not None
        assert adapter.connections_factory is not None

        adapter.post("/orders", CreateOrderAction)
        app = adapter.build()
        assert app["route_count"] == 1
