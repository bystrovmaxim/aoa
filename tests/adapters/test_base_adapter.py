# tests/adapters/test_base_adapter.py
"""
Тесты для BaseAdapter — абстрактного базового класса протокольных адаптеров.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Конструктор:
    - Корректная инициализация с machine и auth_coordinator.
    - Хранение connections_factory.
    - TypeError при передаче не-ActionProductMachine.
    - TypeError при auth_coordinator=None.
    - Пустой список маршрутов при создании.

Протокольные методы (через конкретный тестовый адаптер):
    - Регистрация маршрутов с минимальными параметрами.
    - Регистрация с request_model, response_model, mappers.
    - Множественные маршруты.
    - Fluent chain: методы возвращают self.
    - ValueError при request_model без params_mapper.

build():
    - Возвращает протокольное приложение.
    - Сохраняет порядок маршрутов.
    - Fluent chain завершается build().

Интеграция:
    - Полный цикл: регистрация → build.
    - С мапперами и без.
    - Fluent chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from action_machine.adapters.base_adapter import BaseAdapter
from action_machine.adapters.base_route_record import BaseRouteRecord
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.auth.no_auth_coordinator import NoAuthCoordinator
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta

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
    """Альтернативная модель запроса для тестов маппинга."""
    page: int = Field(default=1, description="Страница")


class AltResponse(BaseResult):
    """Альтернативная модель ответа для тестов маппинга."""
    entries: list = Field(default_factory=list, description="Элементы")


@meta(description="Тестовое действие")
@CheckRoles(CheckRoles.NONE)
class SampleAction(BaseAction[SampleParams, SampleResult]):
    @summary_aspect("Тестовый summary")
    async def summary(self, params, state, box, connections):
        return SampleResult()


@meta(description="Второе тестовое действие")
@CheckRoles(CheckRoles.NONE)
class AnotherAction(BaseAction[SampleParams, SampleResult]):
    @summary_aspect("Другой summary")
    async def summary(self, params, state, box, connections):
        return SampleResult()


def dummy_params_mapper(x: Any) -> Any:
    return x


def dummy_response_mapper(x: Any) -> Any:
    return x


# ═════════════════════════════════════════════════════════════════════════════
# Тестовый конкретный адаптер и RouteRecord
#
# Имена без префикса "Test", чтобы pytest не пытался собрать их
# как тестовые классы (у dataclass и BaseAdapter есть __init__).
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class StubRouteRecord(BaseRouteRecord):
    """Тестовый RouteRecord для проверки BaseAdapter."""
    method: str = "POST"
    path: str = "/"
    tags: tuple[str, ...] = ()
    summary: str = ""


class StubAdapter(BaseAdapter[StubRouteRecord]):
    """
    Конкретный тестовый адаптер для проверки абстрактного BaseAdapter.

    Реализует протокольные методы post() и get() и метод build(),
    возвращающий список зарегистрированных маршрутов.
    """

    def post(
        self,
        path: str,
        action_class: type,
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Any = None,
        response_mapper: Any = None,
        tags: list[str] | None = None,
        summary: str = "",
    ) -> StubAdapter:
        record = StubRouteRecord(
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
        action_class: type,
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Any = None,
        response_mapper: Any = None,
        tags: list[str] | None = None,
        summary: str = "",
    ) -> StubAdapter:
        record = StubRouteRecord(
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

    def build(self) -> list[StubRouteRecord]:
        """Возвращает список зарегистрированных маршрутов."""
        return list(self._routes)


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
def auth() -> NoAuthCoordinator:
    return NoAuthCoordinator()


@pytest.fixture
def adapter(machine, auth) -> StubAdapter:
    return StubAdapter(machine=machine, auth_coordinator=auth)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Конструктор
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseAdapterConstructor:
    """Тесты конструктора BaseAdapter."""

    def test_stores_machine(self, machine, auth):
        adapter = StubAdapter(machine=machine, auth_coordinator=auth)
        assert adapter.machine is machine

    def test_stores_auth_coordinator(self, machine, auth):
        adapter = StubAdapter(machine=machine, auth_coordinator=auth)
        assert adapter.auth_coordinator is auth

    def test_stores_connections_factory(self, machine, auth):
        def factory_fn():
            return {}
        adapter = StubAdapter(
            machine=machine,
            auth_coordinator=auth,
            connections_factory=factory_fn,
        )
        assert adapter.connections_factory is factory_fn

    def test_default_connections_factory_none(self, machine, auth):
        adapter = StubAdapter(machine=machine, auth_coordinator=auth)
        assert adapter.connections_factory is None

    def test_empty_routes(self, machine, auth):
        adapter = StubAdapter(machine=machine, auth_coordinator=auth)
        assert adapter.routes == []

    def test_non_machine_raises_type_error(self, auth):
        with pytest.raises(TypeError, match="ожидает ActionProductMachine"):
            StubAdapter(machine="not a machine", auth_coordinator=auth)

    def test_none_machine_raises_type_error(self, auth):
        with pytest.raises(TypeError, match="ожидает ActionProductMachine"):
            StubAdapter(machine=None, auth_coordinator=auth)

    def test_int_machine_raises_type_error(self, auth):
        with pytest.raises(TypeError, match="ожидает ActionProductMachine"):
            StubAdapter(machine=42, auth_coordinator=auth)

    def test_none_auth_raises_type_error(self, machine):
        with pytest.raises(TypeError, match="auth_coordinator обязателен"):
            StubAdapter(machine=machine, auth_coordinator=None)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Протокольные методы
# ═════════════════════════════════════════════════════════════════════════════


class TestAdapterProtocolMethods:
    """Тесты протокольных методов (post, get)."""

    def test_post_minimal(self, adapter):
        adapter.post("/test", SampleAction)
        assert len(adapter.routes) == 1
        assert adapter.routes[0].method == "POST"
        assert adapter.routes[0].path == "/test"
        assert adapter.routes[0].action_class is SampleAction

    def test_get_minimal(self, adapter):
        adapter.get("/test", SampleAction)
        assert len(adapter.routes) == 1
        assert adapter.routes[0].method == "GET"

    def test_post_with_request_model_and_mapper(self, adapter):
        adapter.post(
            "/test", SampleAction,
            request_model=AltRequest,
            params_mapper=dummy_params_mapper,
        )
        assert adapter.routes[0].request_model is AltRequest
        assert adapter.routes[0].params_mapper is dummy_params_mapper

    def test_get_with_both_models_and_mappers(self, adapter):
        adapter.get(
            "/test", SampleAction,
            request_model=AltRequest,
            response_model=AltResponse,
            params_mapper=dummy_params_mapper,
            response_mapper=dummy_response_mapper,
        )
        r = adapter.routes[0]
        assert r.effective_request_model is AltRequest
        assert r.effective_response_model is AltResponse

    def test_post_with_tags_and_summary(self, adapter):
        adapter.post("/test", SampleAction, tags=["orders"], summary="Создание")
        r = adapter.routes[0]
        assert r.tags == ("orders",)
        assert r.summary == "Создание"

    def test_multiple_routes(self, adapter):
        adapter.post("/a", SampleAction)
        adapter.get("/b", AnotherAction)
        adapter.post("/c", SampleAction)
        assert len(adapter.routes) == 3

    def test_post_different_request_without_mapper_raises(self, adapter):
        with pytest.raises(ValueError, match="params_mapper не указан"):
            adapter.post("/test", SampleAction, request_model=AltRequest)

    def test_fluent_chain_returns_self(self, adapter):
        result = adapter.post("/test", SampleAction)
        assert result is adapter

    def test_fluent_chain_get_returns_self(self, adapter):
        result = adapter.get("/test", SampleAction)
        assert result is adapter

    def test_fluent_chain_multiple(self, adapter):
        result = adapter \
            .post("/a", SampleAction) \
            .get("/b", AnotherAction) \
            .post("/c", SampleAction)
        assert result is adapter
        assert len(adapter.routes) == 3


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: build()
# ═════════════════════════════════════════════════════════════════════════════


class TestBuild:
    """Тесты метода build()."""

    def test_returns_app(self, adapter):
        adapter.post("/test", SampleAction)
        app = adapter.build()
        assert isinstance(app, list)
        assert len(app) == 1

    def test_empty_routes(self, adapter):
        app = adapter.build()
        assert app == []

    def test_preserves_order(self, adapter):
        adapter.post("/first", SampleAction)
        adapter.get("/second", AnotherAction)
        adapter.post("/third", SampleAction)
        app = adapter.build()
        assert [r.path for r in app] == ["/first", "/second", "/third"]

    def test_fluent_chain_to_build(self, adapter):
        app = adapter \
            .post("/a", SampleAction) \
            .get("/b", AnotherAction) \
            .build()
        assert len(app) == 2


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Интеграция
# ═════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Интеграционные тесты полного цикла."""

    def test_full_cycle_minimal(self, adapter):
        app = adapter.post("/orders", SampleAction).build()
        assert len(app) == 1
        assert app[0].action_class is SampleAction
        assert app[0].params_type is SampleParams
        assert app[0].result_type is SampleResult

    def test_full_cycle_with_mappers(self, adapter):
        app = adapter.post(
            "/orders", SampleAction,
            request_model=AltRequest,
            response_model=AltResponse,
            params_mapper=dummy_params_mapper,
            response_mapper=dummy_response_mapper,
        ).build()
        assert app[0].effective_request_model is AltRequest
        assert app[0].effective_response_model is AltResponse

    def test_full_cycle_mixed(self, adapter):
        app = adapter \
            .post("/create", SampleAction) \
            .get("/list", AnotherAction, request_model=AltRequest, params_mapper=dummy_params_mapper) \
            .build()
        assert len(app) == 2
        assert app[0].request_model is None
        assert app[1].request_model is AltRequest

    def test_full_cycle_fluent_chain(self, adapter):
        app = adapter \
            .post("/a", SampleAction, tags=["system"]) \
            .get("/b", AnotherAction, tags=["orders"]) \
            .post("/c", SampleAction, summary="Custom") \
            .build()
        assert len(app) == 3
        assert app[0].tags == ("system",)
        assert app[1].tags == ("orders",)
        assert app[2].summary == "Custom"
