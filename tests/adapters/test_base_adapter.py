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
    - route(): возвращает builder конкретного типа.
    - route(): TypeError при передаче не-класса.
    - route(): TypeError при передаче класса, не наследующего BaseAction.
    - _add_route(): добавляет RouteRecord в _routes.
    - routes: свойство возвращает список зарегистрированных маршрутов.
    - build(): вызывается и возвращает протокольное приложение.
    - Множественная регистрация маршрутов.

BaseRouteRecord:
    - Нельзя инстанцировать напрямую (TypeError).
    - Конкретный наследник создаётся с обязательными полями.
    - Frozen: попытка изменения поля → FrozenInstanceError.
    - Значения по умолчанию: mappers=None.
    - Валидация: params_mapper обязателен если params_type != request_model.
    - Валидация: result_mapper обязателен если result_type != response_model.
    - Валидация: маппер при совпадающих типах допустим (не ошибка).
    - Протокольно-специфичные поля в наследнике типизированы.

Интеграция:
    - Полный цикл: создание адаптера → регистрация маршрутов → build().
    - Builder корректно собирает конфигурацию и вызывает _add_route.
    - Несколько маршрутов с разными action_class.
    - Маршрут с одинаковыми типами (без маппера).
    - Маршрут с разными типами (с маппером).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import Field

from action_machine.adapters.base_adapter import BaseAdapter
from action_machine.adapters.base_route_record import BaseRouteRecord
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
    """Параметры действия для тестов (совпадают с request_model)."""
    pass


class MockResult(BaseResult):
    """Результат действия для тестов (совпадают с response_model)."""
    pass


class OrderParams(BaseParams):
    """Параметры заказа — отличаются от протокольной модели запроса."""
    user_id: str = Field(description="ID пользователя")
    amount: float = Field(description="Сумма заказа")


class OrderResult(BaseResult):
    """Результат заказа — отличается от протокольной модели ответа."""
    order_id: str = Field(description="ID заказа")
    status: str = Field(description="Статус")


class CreateOrderRequest(BaseParams):
    """Протокольная модель запроса (отличается от OrderParams)."""
    user_id: str = Field(description="ID пользователя")
    amount: float = Field(description="Сумма")
    currency: str = Field(default="RUB", description="Валюта")


class CreateOrderResponse(BaseResult):
    """Протокольная модель ответа (отличается от OrderResult)."""
    order_id: str = Field(description="ID заказа")
    status: str = Field(description="Статус")
    message: str = Field(default="", description="Сообщение")


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые функции-мапперы (вместо lambda, для соответствия ruff E731)
# ═════════════════════════════════════════════════════════════════════════════


def map_request_to_order_params(req: Any) -> OrderParams:
    """Преобразует протокольный запрос в OrderParams."""
    return OrderParams(user_id=req.user_id, amount=req.amount)


def map_order_result_to_response(res: Any) -> CreateOrderResponse:
    """Преобразует OrderResult в протокольный ответ."""
    return CreateOrderResponse(order_id=res["order_id"], status=res["status"])


def identity_mapper(x: Any) -> Any:
    """Маппер-тождество для тестов с совпадающими типами."""
    return x


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые действия
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Тестовое действие A")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class SampleActionA(BaseAction[MockParams, MockResult]):
    """Действие A — params_type и request_model совпадают."""

    @summary_aspect("Тест A")
    async def summary(
        self, params: MockParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> MockResult:
        return MockResult()


@meta(description="Тестовое действие B")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class SampleActionB(BaseAction[MockParams, MockResult]):
    """Действие B — для проверки множественной регистрации."""

    @summary_aspect("Тест B")
    async def summary(
        self, params: MockParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> MockResult:
        return MockResult()


@meta(description="Действие с отличающимися типами params/result")
@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
class OrderAction(BaseAction[OrderParams, OrderResult]):
    """Действие с OrderParams/OrderResult, отличающимися от протокольных моделей."""

    @summary_aspect("Создание заказа")
    async def summary(
        self, params: OrderParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> OrderResult:
        return OrderResult(order_id="ORD-1", status="created")


class NotAnAction:
    """Класс, не наследующий BaseAction — для проверки TypeError."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Конкретный RouteRecord для тестов
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MockRouteRecord(BaseRouteRecord):
    """
    Конкретный RouteRecord для тестов.

    Содержит протокольно-специфичные поля, имитирующие HTTP-адаптер.
    """
    method: str = "GET"
    path: str = "/"
    tags: tuple[str, ...] = ()
    summary: str = ""


# ═════════════════════════════════════════════════════════════════════════════
# Mock fluent-builder для тестов
# ═════════════════════════════════════════════════════════════════════════════


class MockRouteBuilder:
    """
    Mock fluent-builder для тестов.

    Имитирует протокольно-специфичный builder с цепочкой вызовов.
    При ``register()`` создаёт MockRouteRecord и добавляет в адаптер.
    """

    def __init__(
        self,
        adapter: MockAdapter,
        action_class: type[BaseAction[Any, Any]],
    ) -> None:
        self._adapter = adapter
        self._action_class = action_class
        self._method: str = "GET"
        self._path: str = "/"
        self._tags: tuple[str, ...] = ()
        self._summary: str = ""
        self._params_type_cls: type | None = None
        self._result_type_cls: type | None = None
        self._request_model_cls: type | None = None
        self._response_model_cls: type | None = None
        self._params_mapper_fn = None
        self._result_mapper_fn = None

    def post(self, path: str) -> MockRouteBuilder:
        """Устанавливает метод POST и путь."""
        self._method = "POST"
        self._path = path
        return self

    def get(self, path: str) -> MockRouteBuilder:
        """Устанавливает метод GET и путь."""
        self._method = "GET"
        self._path = path
        return self

    def tags(self, tag_list: list[str]) -> MockRouteBuilder:
        """Устанавливает теги маршрута."""
        self._tags = tuple(tag_list)
        return self

    def summary(self, text: str) -> MockRouteBuilder:
        """Устанавливает описание маршрута."""
        self._summary = text
        return self

    def params_type(self, cls: type) -> MockRouteBuilder:
        """Устанавливает тип параметров действия."""
        self._params_type_cls = cls
        return self

    def result_type(self, cls: type) -> MockRouteBuilder:
        """Устанавливает тип результата действия."""
        self._result_type_cls = cls
        return self

    def request_model(self, cls: type) -> MockRouteBuilder:
        """Устанавливает модель запроса."""
        self._request_model_cls = cls
        return self

    def response_model(self, cls: type) -> MockRouteBuilder:
        """Устанавливает модель ответа."""
        self._response_model_cls = cls
        return self

    def params_mapper(self, fn: Any) -> MockRouteBuilder:
        """Устанавливает маппер параметров."""
        self._params_mapper_fn = fn
        return self

    def result_mapper(self, fn: Any) -> MockRouteBuilder:
        """Устанавливает маппер результата."""
        self._result_mapper_fn = fn
        return self

    def register(self) -> None:
        """
        Завершает конфигурацию и добавляет MockRouteRecord в адаптер.

        Если params_type и request_model не указаны, использует
        MockParams как значение по умолчанию.
        """
        p_type = self._params_type_cls or MockParams
        r_type = self._result_type_cls or MockResult
        req_model = self._request_model_cls or p_type
        resp_model = self._response_model_cls or r_type

        record = MockRouteRecord(
            action_class=self._action_class,
            params_type=p_type,
            result_type=r_type,
            request_model=req_model,
            response_model=resp_model,
            params_mapper=self._params_mapper_fn,
            result_mapper=self._result_mapper_fn,
            method=self._method,
            path=self._path,
            tags=self._tags,
            summary=self._summary,
        )
        self._adapter._add_route(record)


# ═════════════════════════════════════════════════════════════════════════════
# Mock-адаптер для тестов
# ═════════════════════════════════════════════════════════════════════════════


class MockAdapter(BaseAdapter[MockRouteBuilder, MockRouteRecord]):
    """
    Mock-адаптер для тестирования BaseAdapter.

    Реализует абстрактные методы: _create_builder() возвращает
    MockRouteBuilder, build() возвращает словарь с маршрутами.
    """

    def _create_builder(
        self, action_class: type[BaseAction[Any, Any]],
    ) -> MockRouteBuilder:
        """Создаёт MockRouteBuilder."""
        return MockRouteBuilder(adapter=self, action_class=action_class)

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
# ТЕСТЫ: route()
# ═════════════════════════════════════════════════════════════════════════════


class TestRoute:
    """Тесты метода route()."""

    def test_returns_builder(self, adapter: MockAdapter):
        """route() возвращает MockRouteBuilder."""
        builder = adapter.route(SampleActionA)
        assert isinstance(builder, MockRouteBuilder)

    def test_instance_raises_type_error(self, adapter: MockAdapter):
        """route() с экземпляром (не классом) → TypeError."""
        with pytest.raises(TypeError, match="ожидает класс"):
            adapter.route(SampleActionA())

    def test_string_raises_type_error(self, adapter: MockAdapter):
        """route() со строкой → TypeError."""
        with pytest.raises(TypeError, match="ожидает класс"):
            adapter.route("SampleActionA")

    def test_non_base_action_raises_type_error(self, adapter: MockAdapter):
        """route() с классом без BaseAction → TypeError."""
        with pytest.raises(TypeError, match="ожидает наследника BaseAction"):
            adapter.route(NotAnAction)

    def test_none_raises_type_error(self, adapter: MockAdapter):
        """route() с None → TypeError."""
        with pytest.raises(TypeError, match="ожидает класс"):
            adapter.route(None)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: BaseRouteRecord
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseRouteRecord:
    """Тесты BaseRouteRecord через конкретный MockRouteRecord."""

    def test_cannot_instantiate_base_directly(self):
        """BaseRouteRecord нельзя инстанцировать напрямую → TypeError."""
        with pytest.raises(TypeError, match="нельзя инстанцировать напрямую"):
            BaseRouteRecord(
                action_class=SampleActionA,
                params_type=MockParams,
                result_type=MockResult,
                request_model=MockParams,
                response_model=MockResult,
            )

    def test_create_concrete_with_same_types(self):
        """Наследник создаётся когда params_type == request_model."""
        record = MockRouteRecord(
            action_class=SampleActionA,
            params_type=MockParams,
            result_type=MockResult,
            request_model=MockParams,
            response_model=MockResult,
        )
        assert record.action_class is SampleActionA
        assert record.params_type is MockParams
        assert record.result_type is MockResult
        assert record.request_model is MockParams
        assert record.response_model is MockResult
        assert record.params_mapper is None
        assert record.result_mapper is None

    def test_create_concrete_with_different_types_and_mappers(self):
        """Наследник создаётся когда типы различаются и мапперы указаны."""
        record = MockRouteRecord(
            action_class=OrderAction,
            params_type=OrderParams,
            result_type=OrderResult,
            request_model=CreateOrderRequest,
            response_model=CreateOrderResponse,
            params_mapper=map_request_to_order_params,
            result_mapper=map_order_result_to_response,
            method="POST",
            path="/api/orders",
        )
        assert record.params_mapper is map_request_to_order_params
        assert record.result_mapper is map_order_result_to_response
        assert record.method == "POST"
        assert record.path == "/api/orders"

    def test_frozen_prevents_modification(self):
        """Frozen: попытка изменения поля → FrozenInstanceError."""
        record = MockRouteRecord(
            action_class=SampleActionA,
            params_type=MockParams,
            result_type=MockResult,
            request_model=MockParams,
            response_model=MockResult,
        )
        with pytest.raises(FrozenInstanceError):
            record.action_class = SampleActionB

    def test_frozen_prevents_path_modification(self):
        """Frozen: попытка изменения протокольного поля → FrozenInstanceError."""
        record = MockRouteRecord(
            action_class=SampleActionA,
            params_type=MockParams,
            result_type=MockResult,
            request_model=MockParams,
            response_model=MockResult,
            path="/original",
        )
        with pytest.raises(FrozenInstanceError):
            record.path = "/modified"

    def test_protocol_specific_fields_defaults(self):
        """Протокольно-специфичные поля типизированы и имеют дефолты."""
        record = MockRouteRecord(
            action_class=SampleActionA,
            params_type=MockParams,
            result_type=MockResult,
            request_model=MockParams,
            response_model=MockResult,
        )
        assert record.method == "GET"
        assert record.path == "/"
        assert record.tags == ()
        assert record.summary == ""

    def test_protocol_specific_fields_custom(self):
        """Протокольно-специфичные поля принимают пользовательские значения."""
        record = MockRouteRecord(
            action_class=SampleActionA,
            params_type=MockParams,
            result_type=MockResult,
            request_model=MockParams,
            response_model=MockResult,
            method="POST",
            path="/api/v1/orders",
            tags=("orders", "create"),
            summary="Создание заказа",
        )
        assert record.method == "POST"
        assert record.path == "/api/v1/orders"
        assert record.tags == ("orders", "create")
        assert record.summary == "Создание заказа"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Валидация инвариантов маппинга
# ═════════════════════════════════════════════════════════════════════════════


class TestRouteRecordMapperValidation:
    """Тесты валидации инвариантов params_mapper и result_mapper."""

    def test_different_params_without_mapper_raises(self):
        """params_type != request_model и params_mapper=None → ValueError."""
        with pytest.raises(ValueError, match="params_mapper не указан"):
            MockRouteRecord(
                action_class=OrderAction,
                params_type=OrderParams,
                result_type=MockResult,
                request_model=CreateOrderRequest,
                response_model=MockResult,
            )

    def test_different_result_without_mapper_raises(self):
        """result_type != response_model и result_mapper=None → ValueError."""
        with pytest.raises(ValueError, match="result_mapper не указан"):
            MockRouteRecord(
                action_class=OrderAction,
                params_type=MockParams,
                result_type=OrderResult,
                request_model=MockParams,
                response_model=CreateOrderResponse,
            )

    def test_both_different_without_mappers_raises(self):
        """Оба типа различаются, оба маппера отсутствуют → ValueError (params первый)."""
        with pytest.raises(ValueError, match="params_mapper не указан"):
            MockRouteRecord(
                action_class=OrderAction,
                params_type=OrderParams,
                result_type=OrderResult,
                request_model=CreateOrderRequest,
                response_model=CreateOrderResponse,
            )

    def test_same_types_without_mappers_ok(self):
        """params_type is request_model и result_type is response_model → OK."""
        record = MockRouteRecord(
            action_class=SampleActionA,
            params_type=MockParams,
            result_type=MockResult,
            request_model=MockParams,
            response_model=MockResult,
        )
        assert record.params_mapper is None
        assert record.result_mapper is None

    def test_same_types_with_mappers_ok(self):
        """Маппер при совпадающих типах допустим (дополнительная трансформация)."""
        record = MockRouteRecord(
            action_class=SampleActionA,
            params_type=MockParams,
            result_type=MockResult,
            request_model=MockParams,
            response_model=MockResult,
            params_mapper=identity_mapper,
            result_mapper=identity_mapper,
        )
        assert record.params_mapper is identity_mapper
        assert record.result_mapper is identity_mapper

    def test_different_params_with_mapper_ok(self):
        """params_type != request_model с маппером → OK."""
        record = MockRouteRecord(
            action_class=OrderAction,
            params_type=OrderParams,
            result_type=MockResult,
            request_model=CreateOrderRequest,
            response_model=MockResult,
            params_mapper=map_request_to_order_params,
        )
        assert record.params_mapper is map_request_to_order_params

    def test_different_result_with_mapper_ok(self):
        """result_type != response_model с маппером → OK."""
        record = MockRouteRecord(
            action_class=OrderAction,
            params_type=MockParams,
            result_type=OrderResult,
            request_model=MockParams,
            response_model=CreateOrderResponse,
            result_mapper=map_order_result_to_response,
        )
        assert record.result_mapper is map_order_result_to_response


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Регистрация маршрутов через builder
# ═════════════════════════════════════════════════════════════════════════════


class TestRouteRegistration:
    """Тесты регистрации маршрутов через fluent-builder."""

    def test_register_adds_route(self, adapter: MockAdapter):
        """register() добавляет MockRouteRecord в _routes."""
        adapter.route(SampleActionA) \
            .post("/api/test") \
            .register()

        assert len(adapter.routes) == 1
        record = adapter.routes[0]
        assert isinstance(record, MockRouteRecord)
        assert record.action_class is SampleActionA
        assert record.method == "POST"
        assert record.path == "/api/test"

    def test_register_multiple(self, adapter: MockAdapter):
        """Несколько маршрутов регистрируются независимо."""
        adapter.route(SampleActionA).post("/api/a").register()
        adapter.route(SampleActionB).get("/api/b").register()

        assert len(adapter.routes) == 2
        assert adapter.routes[0].action_class is SampleActionA
        assert adapter.routes[0].method == "POST"
        assert adapter.routes[1].action_class is SampleActionB
        assert adapter.routes[1].method == "GET"

    def test_register_with_all_options(self, adapter: MockAdapter):
        """Регистрация с полным набором опций builder."""
        adapter.route(OrderAction) \
            .post("/api/orders") \
            .tags(["orders", "create"]) \
            .summary("Создание заказа") \
            .params_type(OrderParams) \
            .result_type(OrderResult) \
            .request_model(CreateOrderRequest) \
            .response_model(CreateOrderResponse) \
            .params_mapper(map_request_to_order_params) \
            .result_mapper(map_order_result_to_response) \
            .register()

        record = adapter.routes[0]
        assert record.action_class is OrderAction
        assert record.params_type is OrderParams
        assert record.result_type is OrderResult
        assert record.request_model is CreateOrderRequest
        assert record.response_model is CreateOrderResponse
        assert record.params_mapper is map_request_to_order_params
        assert record.result_mapper is map_order_result_to_response
        assert record.method == "POST"
        assert record.path == "/api/orders"
        assert record.tags == ("orders", "create")
        assert record.summary == "Создание заказа"

    def test_register_minimal(self, adapter: MockAdapter):
        """Минимальная регистрация — только action_class."""
        adapter.route(SampleActionA).register()

        record = adapter.routes[0]
        assert record.action_class is SampleActionA
        assert record.params_type is MockParams
        assert record.result_type is MockResult
        assert record.request_model is MockParams
        assert record.response_model is MockResult
        assert record.params_mapper is None
        assert record.result_mapper is None
        assert record.method == "GET"
        assert record.path == "/"

    def test_fluent_chain_returns_builder(self, adapter: MockAdapter):
        """Каждый метод builder возвращает self для цепочки."""
        builder = adapter.route(SampleActionA)
        result = builder.post("/api").tags(["x"]).summary("y")
        assert result is builder


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: build()
# ═════════════════════════════════════════════════════════════════════════════


class TestBuild:
    """Тесты метода build()."""

    def test_returns_app(self, adapter: MockAdapter):
        """build() возвращает протокольное приложение."""
        adapter.route(SampleActionA).get("/ping").register()
        app = adapter.build()
        assert app["route_count"] == 1

    def test_empty_routes(self, adapter: MockAdapter):
        """build() без маршрутов возвращает пустое приложение."""
        app = adapter.build()
        assert app["route_count"] == 0
        assert app["routes"] == []

    def test_preserves_order(self, adapter: MockAdapter):
        """build() сохраняет порядок регистрации."""
        adapter.route(SampleActionA).get("/first").register()
        adapter.route(SampleActionB).post("/second").register()

        app = adapter.build()
        assert app["routes"][0].path == "/first"
        assert app["routes"][1].path == "/second"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Интеграция — полный цикл
# ═════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Интеграционные тесты: создание → регистрация → build."""

    def test_full_cycle_same_types(self, adapter: MockAdapter):
        """Полный цикл с совпадающими типами (без маппера)."""
        adapter.route(SampleActionA) \
            .post("/api/v1/action-a") \
            .tags(["test"]) \
            .summary("Действие A") \
            .register()

        adapter.route(SampleActionB) \
            .get("/api/v1/action-b") \
            .register()

        app = adapter.build()
        assert app["route_count"] == 2

        r0 = app["routes"][0]
        assert r0.action_class is SampleActionA
        assert r0.method == "POST"
        assert r0.path == "/api/v1/action-a"
        assert r0.params_mapper is None
        assert r0.result_mapper is None

        r1 = app["routes"][1]
        assert r1.action_class is SampleActionB
        assert r1.method == "GET"
        assert r1.path == "/api/v1/action-b"

    def test_full_cycle_different_types(self, adapter: MockAdapter):
        """Полный цикл с различающимися типами (с маппером)."""
        adapter.route(OrderAction) \
            .post("/api/orders") \
            .params_type(OrderParams) \
            .result_type(OrderResult) \
            .request_model(CreateOrderRequest) \
            .response_model(CreateOrderResponse) \
            .params_mapper(map_request_to_order_params) \
            .result_mapper(map_order_result_to_response) \
            .register()

        app = adapter.build()
        record = app["routes"][0]
        assert record.params_mapper is map_request_to_order_params
        assert record.result_mapper is map_order_result_to_response

    def test_adapter_with_auth_and_connections(self, machine: ActionProductMachine):
        """Адаптер с auth_coordinator и connections_factory."""
        adapter = MockAdapter(
            machine=machine,
            auth_coordinator=MagicMock(),
            connections_factory=MagicMock(return_value={"db": MagicMock()}),
        )

        assert adapter.auth_coordinator is not None
        assert adapter.connections_factory is not None

        adapter.route(SampleActionA).register()
        app = adapter.build()
        assert app["route_count"] == 1
