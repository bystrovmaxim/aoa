# src/action_machine/adapters/base_adapter.py
"""
BaseAdapter[R] — абстрактный базовый класс для всех протокольных адаптеров.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseAdapter — единый контракт для адаптеров, преобразующих внешние протоколы
(HTTP, MCP, gRPC, CLI) в вызовы ``machine.run(context, action, params, connections)``.

Адаптер предоставляет лаконичный fluent API для регистрации маршрутов.
Каждый протокольный метод (post, get, tool и т.д.) — это один вызов,
принимающий путь, класс действия и опциональные параметры маппинга.

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

    2. Регистрация маршрутов:
       adapter.post("/orders/create", CreateOrderAction)
       adapter.get("/orders/list", ListOrdersAction, ListOrdersRequest, params_mapper)
       adapter.get("/orders/{id}", GetOrderAction, GetRequest, GetResponse, p_map, r_map)

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
    │  _add_route(record: R)               │
    │  build() → Any                       │  (абстрактный)
    └──────────────────────────────────────┘
               ▲
               │  наследование
    ┌──────────┴──────────────────────────┐
    │  FastAPIAdapter                      │
    │    post(path, action, ...)           │
    │    get(path, action, ...)            │
    │    build() → FastAPI                 │
    ├──────────────────────────────────────┤
    │  MCPAdapter                          │
    │    tool(name, action, ...)           │
    │    build() → MCPServer               │
    └──────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР КОНКРЕТНОГО АДАПТЕРА (БУДУЩЕЕ)
═══════════════════════════════════════════════════════════════════════════════

    class FastAPIAdapter(BaseAdapter[FastAPIRouteRecord]):

        def post(self, path, action_class, request_model=None,
                 response_model=None, params_mapper=None, result_mapper=None,
                 tags=None, summary=""):
            record = FastAPIRouteRecord(
                action_class=action_class,
                request_model=request_model,
                response_model=response_model,
                params_mapper=params_mapper,
                result_mapper=result_mapper,
                method="POST",
                path=path,
                tags=tuple(tags or ()),
                summary=summary,
            )
            self._add_route(record)

        def build(self):
            app = FastAPI()
            for record in self._routes:
                self._register_endpoint(app, record)
            return app

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ (БУДУЩЕЕ)
═══════════════════════════════════════════════════════════════════════════════

    adapter = FastAPIAdapter(machine=machine, auth_coordinator=auth)

    # Минимум — request_model совпадает с params_type:
    adapter.post("/orders/create", CreateOrderAction)

    # request_model отличается — нужен params_mapper:
    adapter.get("/orders/list", ListOrdersAction,
                request_model=ListOrdersRequest,
                params_mapper=map_list_request_to_params)

    # Оба отличаются — нужны оба маппера:
    adapter.get("/orders/{id}", GetOrderAction,
                request_model=GetOrderRequest,
                response_model=GetOrderResponse,
                params_mapper=map_get_request,
                result_mapper=map_get_response)

    app = adapter.build()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

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

    Fluent-builder убран. Каждый протокольный метод конкретного адаптера —
    это один вызов, принимающий путь, класс действия и опциональные
    параметры маппинга.

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
    # Внутренний метод регистрации
    # ─────────────────────────────────────────────────────────────────────

    def _add_route(self, record: R) -> None:
        """
        Добавляет RouteRecord в список маршрутов.

        Внутренний метод, вызываемый из протокольных методов конкретного
        адаптера (post, get, tool и т.д.). Не предназначен для прямого
        использования разработчиком приложения.

        Аргументы:
            record: конфигурация маршрута — конкретный наследник
                    BaseRouteRecord с протокольно-специфичными полями.
        """
        self._routes.append(record)

    # ─────────────────────────────────────────────────────────────────────
    # Абстрактные методы
    # ─────────────────────────────────────────────────────────────────────

    @abstractmethod
    def build(self) -> Any:
        """
        Создаёт протокольное приложение из зарегистрированных маршрутов.

        Абстрактный метод. Каждый конкретный адаптер реализует его,
        обходя ``_routes`` и генерируя протокольные эндпоинты.

        Возвращает:
            Протокольное приложение. Тип определяется конкретным адаптером:
            - FastAPIAdapter.build() → FastAPI
            - MCPAdapter.build() → MCPServer
        """
