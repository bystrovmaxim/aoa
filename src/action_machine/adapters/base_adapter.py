# src/action_machine/adapters/base_adapter.py
"""
BaseAdapter[R] — абстрактный базовый класс для всех протокольных адаптеров.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseAdapter — единый контракт для адаптеров, преобразующих внешние протоколы
(HTTP, MCP, gRPC, CLI) в вызовы ``machine.run(context, action, params, connections)``.

Адаптер предоставляет fluent API для регистрации маршрутов. Каждый
протокольный метод (post, get, tool и т.д.) возвращает self, что позволяет
строить цепочки вызовов:

    app = adapter \\
        .get("/ping", PingAction) \\
        .post("/orders", CreateOrderAction) \\
        .build()

═══════════════════════════════════════════════════════════════════════════════
GENERIC-ПАРАМЕТР R
═══════════════════════════════════════════════════════════════════════════════

R — тип конкретного RouteRecord (наследника BaseRouteRecord), который
создаёт адаптер при регистрации маршрута:

    FastAPIAdapter → FastAPIRouteRecord (method, path, tags, summary, ...)
    MCPAdapter     → MCPRouteRecord (tool_name, description, ...)

Типизация ``_routes: list[R]`` обеспечивает корректное автодополнение
и проверку типов при обходе маршрутов в ``build()``.

═══════════════════════════════════════════════════════════════════════════════
АВТОИЗВЛЕЧЕНИЕ ТИПОВ
═══════════════════════════════════════════════════════════════════════════════

params_type и result_type ВСЕГДА извлекаются автоматически из generic-
параметров BaseAction[P, R] класса действия. Разработчик никогда не
указывает их вручную. Если протокольные модели (request_model, response_model)
совпадают с params_type/result_type — они не указываются вовсе. Мапперы
нужны только когда модели различаются.

═══════════════════════════════════════════════════════════════════════════════
КОНВЕНЦИЯ ИМЕНОВАНИЯ МАППЕРОВ
═══════════════════════════════════════════════════════════════════════════════

Каждый маппер назван по тому, что он ВОЗВРАЩАЕТ:

    params_mapper   → возвращает params   (преобразует request → params)
    response_mapper → возвращает response (преобразует result  → response)

═══════════════════════════════════════════════════════════════════════════════
КОНСТРУКТОР
═══════════════════════════════════════════════════════════════════════════════

    machine : ActionProductMachine
        Машина выполнения действий. Обязательный параметр.

    auth_coordinator : AuthCoordinator | None
        Координатор аутентификации. Если указан, адаптер вызывает
        auth_coordinator.process(request_data) для создания Context.
        Если None — Context создаётся пустым.

    connections_factory : Callable[..., dict[str, BaseResourceManager]] | None
        Фабрика соединений. Если указана, вызывается перед каждым
        machine.run(). Если None — connections не передаются.

═══════════════════════════════════════════════════════════════════════════════
FLUENT API
═══════════════════════════════════════════════════════════════════════════════

Метод ``_add_route(record)`` возвращает ``self``, что позволяет конкретным
адаптерам строить цепочки через ``return self._add_route(record)``
в протокольных методах (post, get, tool и т.д.).

Метод ``build()`` завершает цепочку и возвращает протокольное приложение.

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Обработка ошибок — ответственность конкретного адаптера. Он перехватывает
исключения ActionMachine (AuthorizationError, ValidationFieldError и др.)
в except-блоках и самостоятельно преобразует их в протокольные ответы.

    Пример для FastAPI:
        except AuthorizationError as exc:
            return JSONResponse(status_code=403, content={"error": str(exc)})
        except ValidationFieldError as exc:
            return JSONResponse(status_code=422, content={"error": str(exc)})

═══════════════════════════════════════════════════════════════════════════════
ЖИЗНЕННЫЙ ЦИКЛ
═══════════════════════════════════════════════════════════════════════════════

    1. Создание адаптера:
       adapter = FastAPIAdapter(machine=machine, auth_coordinator=auth)

    2. Регистрация маршрутов (fluent chain):
       adapter \\
           .post("/orders/create", CreateOrderAction) \\
           .get("/orders/list", ListOrdersAction,
                request_model=ListOrdersRequest,
                params_mapper=map_list_request) \\
           .get("/orders/{id}", GetOrderAction,
                request_model=GetRequest,
                response_model=GetResponse,
                params_mapper=map_get_request,
                response_mapper=map_get_response)

    3. Построение приложения:
       app = adapter.build()

    4. Запуск:
       uvicorn.run(app, ...)

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────┐
    │  BaseAdapter[R]                      │
    │                                      │
    │  machine: ActionProductMachine       │
    │  auth_coordinator: Auth | None       │
    │  connections_factory: Fn | None      │
    │  _routes: list[R]                    │
    │                                      │
    │  _add_route(record: R) → Self        │
    │  build() → Any                       │  (абстрактный)
    └──────────────────────────────────────┘
               ▲
               │  наследование
    ┌──────────┴──────────────────────────┐
    │  FastAPIAdapter                      │
    │    post(path, action, ...) → Self    │
    │    get(path, action, ...) → Self     │
    │    build() → FastAPI                 │
    ├──────────────────────────────────────┤
    │  MCPAdapter                          │
    │    tool(name, action, ...) → Self    │
    │    build() → MCPServer               │
    └──────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ (FLUENT CHAIN)
═══════════════════════════════════════════════════════════════════════════════

    adapter = FastAPIAdapter(machine=machine, auth_coordinator=auth)

    app = adapter \\
        .post("/orders/create", CreateOrderAction) \\
        .get("/orders/list", ListOrdersAction,
             request_model=ListOrdersRequest,
             params_mapper=map_list_request_to_params) \\
        .get("/orders/{id}", GetOrderAction,
             request_model=GetRequest,
             response_model=GetResponse,
             params_mapper=map_get_request,
             response_mapper=map_get_response) \\
        .build()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Self

from action_machine.auth.auth_coordinator import AuthCoordinator
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .base_route_record import BaseRouteRecord


class BaseAdapter[R: BaseRouteRecord](ABC):
    """
    Абстрактный базовый класс для всех протокольных адаптеров ActionMachine.

    Определяет контракт: хранение RouteRecord, построение протокольного
    приложения. Конкретные адаптеры наследуют BaseAdapter и реализуют
    протокольные методы регистрации (post, get, tool) и build().

    Fluent API: протокольные методы конкретного адаптера возвращают self
    для построения цепочек вызовов. Метод ``_add_route()`` возвращает self.

    Обработка ошибок — ответственность конкретного адаптера через
    except-блоки.

    Атрибуты:
        _machine : ActionProductMachine
            Машина выполнения действий.

        _auth_coordinator : AuthCoordinator | None
            Координатор аутентификации.

        _connections_factory : Callable[..., dict[str, BaseResourceManager]] | None
            Фабрика соединений.

        _routes : list[R]
            Список зарегистрированных маршрутов. Типизирован конкретным
            наследником BaseRouteRecord.
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: AuthCoordinator | None = None,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
    ) -> None:
        """
        Инициализирует адаптер.

        Аргументы:
            machine: машина выполнения действий. Обязательный параметр.
            auth_coordinator: координатор аутентификации. Если None —
                              Context создаётся пустым.
            connections_factory: фабрика соединений. Если None —
                                 connections не передаются.

        Исключения:
            TypeError: если machine не является экземпляром ActionProductMachine.
        """
        if not isinstance(machine, ActionProductMachine):
            raise TypeError(
                f"BaseAdapter ожидает ActionProductMachine, "
                f"получен {type(machine).__name__}: {machine!r}."
            )

        self._machine: ActionProductMachine = machine
        self._auth_coordinator: AuthCoordinator | None = auth_coordinator
        self._connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = connections_factory
        self._routes: list[R] = []

    # ─────────────────────────────────────────────────────────────────────
    # Свойства (только чтение)
    # ─────────────────────────────────────────────────────────────────────

    @property
    def machine(self) -> ActionProductMachine:
        """Возвращает машину выполнения действий."""
        return self._machine

    @property
    def auth_coordinator(self) -> AuthCoordinator | None:
        """Возвращает координатор аутентификации (или None)."""
        return self._auth_coordinator

    @property
    def connections_factory(self) -> Callable[..., dict[str, BaseResourceManager]] | None:
        """Возвращает фабрику соединений (или None)."""
        return self._connections_factory

    @property
    def routes(self) -> list[R]:
        """
        Возвращает список зарегистрированных маршрутов.

        Каждый элемент — конкретный наследник BaseRouteRecord
        с типизированными протокольно-специфичными полями.
        """
        return self._routes

    # ─────────────────────────────────────────────────────────────────────
    # Внутренний метод регистрации (fluent)
    # ─────────────────────────────────────────────────────────────────────

    def _add_route(self, record: R) -> Self:
        """
        Добавляет RouteRecord в список маршрутов и возвращает self.

        Возврат self обеспечивает fluent API: протокольные методы
        конкретного адаптера делают ``return self._add_route(record)``
        и тем самым поддерживают цепочки вызовов.

        Внутренний метод, вызываемый из протокольных методов конкретного
        адаптера (post, get, tool и т.д.). Не предназначен для прямого
        использования разработчиком приложения.

        Аргументы:
            record: конфигурация маршрута — конкретный наследник
                    BaseRouteRecord с протокольно-специфичными полями.

        Возвращает:
            Self — текущий экземпляр адаптера для fluent chain.
        """
        self._routes.append(record)
        return self

    # ─────────────────────────────────────────────────────────────────────
    # Абстрактные методы
    # ─────────────────────────────────────────────────────────────────────

    @abstractmethod
    def build(self) -> Any:
        """
        Создаёт протокольное приложение из зарегистрированных маршрутов.

        Абстрактный метод. Каждый конкретный адаптер реализует его,
        обходя ``_routes`` и генерируя протокольные эндпоинты.

        Этот метод завершает fluent chain и возвращает готовое приложение.

        Возвращает:
            Протокольное приложение. Тип определяется конкретным адаптером:
            - FastAPIAdapter.build() → FastAPI
            - MCPAdapter.build() → MCPServer
        """
