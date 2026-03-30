# src/action_machine/adapters/base_adapter.py
"""
BaseAdapter[B, R] — абстрактный базовый класс для всех протокольных адаптеров.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseAdapter — единый контракт для адаптеров, преобразующих внешние протоколы
(HTTP, MCP, gRPC, CLI) в вызовы ``machine.run(context, action, params, connections)``.

Адаптер отвечает за:

1. РЕГИСТРАЦИЮ МАРШРУТОВ: метод ``route(action_class)`` создаёт
   fluent-builder, через который разработчик настраивает маршрут.
   После вызова ``builder.register()`` маршрут сохраняется в ``_routes``.

2. ПОСТРОЕНИЕ ПРИЛОЖЕНИЯ: метод ``build()`` создаёт протокольное
   приложение (FastAPI app, MCP server, gRPC servicer) на основе
   зарегистрированных маршрутов.

3. ОБРАБОТКУ ОШИБОК: конкретный адаптер самостоятельно перехватывает
   исключения ActionMachine (AuthorizationError, ValidationFieldError
   и др.) в except-блоках и преобразует их в протокольные ответы.

═══════════════════════════════════════════════════════════════════════════════
GENERIC-ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

B — тип fluent-builder для конкретного протокола:
    FastAPIAdapter → FastAPIRouteBuilder (post, get, tags, summary, ...)
    MCPAdapter     → MCPRouteBuilder (tool_name, description, ...)

R — тип конкретного RouteRecord (наследника BaseRouteRecord):
    FastAPIAdapter → FastAPIRouteRecord (method, path, tags, summary, ...)
    MCPAdapter     → MCPRouteRecord (tool_name, description, ...)

Builder создаётся внутри ``route()`` через абстрактный ``_create_builder()``.
При ``register()`` builder создаёт конкретный RouteRecord и добавляет
его в ``_routes``.

═══════════════════════════════════════════════════════════════════════════════
КОНСТРУКТОР
═══════════════════════════════════════════════════════════════════════════════

    machine : ActionProductMachine
        Машина выполнения действий. Обязательный параметр. Адаптер
        делегирует выполнение действий в machine.run().

    auth_coordinator : AuthCoordinator | None
        Координатор аутентификации. Если указан, адаптер вызывает
        auth_coordinator.process(request_data) для создания Context
        перед каждым вызовом machine.run(). Если None — Context
        создаётся пустым (без аутентификации).

    connections_factory : Callable[..., dict[str, BaseResourceManager]] | None
        Фабрика соединений. Если указана, адаптер вызывает
        connections_factory() для получения словаря соединений
        перед каждым вызовом machine.run(). Если None — connections
        передаётся как None.

═══════════════════════════════════════════════════════════════════════════════
ЖИЗНЕННЫЙ ЦИКЛ
═══════════════════════════════════════════════════════════════════════════════

    1. Создание адаптера:
       adapter = ConcreteAdapter(machine=machine, auth_coordinator=auth)

    2. Регистрация маршрутов (повторяется для каждого действия):
       adapter.route(ActionClass).post("/path").params_mapper(...).register()

    3. Построение приложения:
       app = adapter.build()

    4. Запуск (протокольно-специфичный):
       uvicorn.run(app, ...)        # FastAPI
       server.serve_forever()       # MCP

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────┐
    │  BaseAdapter[B, R]                   │
    │                                      │
    │  machine: ActionProductMachine       │
    │  auth_coordinator: Auth | None       │
    │  connections_factory: Fn | None      │
    │  _routes: list[R]                    │
    │                                      │
    │  route(action_class) → B             │
    │  build() → Any                       │
    │  _add_route(record: R)               │
    │  _create_builder(cls) → B            │
    └──────────────────────────────────────┘
               ▲
               │  наследование
    ┌──────────┴──────────────┐
    │  FastAPIAdapter          │
    │  MCPAdapter              │
    └──────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР СОЗДАНИЯ КОНКРЕТНОГО АДАПТЕРА
═══════════════════════════════════════════════════════════════════════════════

    class FastAPIAdapter(BaseAdapter[FastAPIRouteBuilder, FastAPIRouteRecord]):

        def _create_builder(self, action_class):
            return FastAPIRouteBuilder(adapter=self, action_class=action_class)

        def build(self):
            app = FastAPI()
            for record in self._routes:
                self._register_endpoint(app, record)
            return app

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    machine = ActionProductMachine(mode="production", coordinator=coordinator)
    auth = AuthCoordinator(extractor, authenticator, assembler)

    adapter = FastAPIAdapter(
        machine=machine,
        auth_coordinator=auth,
        connections_factory=lambda: {"db": postgres_manager},
    )

    adapter.route(CreateOrderAction) \\
        .post("/api/v1/orders") \\
        .tags(["orders"]) \\
        .params_mapper(lambda req: OrderParams(...)) \\
        .result_mapper(lambda res: CreateOrderResponse(...)) \\
        .register()

    app = adapter.build()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from action_machine.auth.auth_coordinator import AuthCoordinator
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .base_route_record import BaseRouteRecord


class BaseAdapter[B, R: BaseRouteRecord](ABC):
    """
    Абстрактный базовый класс для всех протокольных адаптеров ActionMachine.

    Определяет контракт: регистрация маршрутов через fluent-builder,
    хранение конкретных RouteRecord, построение протокольного приложения.

    Конкретные адаптеры наследуют BaseAdapter и реализуют
    ``_create_builder()`` и ``build()``.

    Обработка ошибок — ответственность конкретного адаптера. Он
    перехватывает исключения ActionMachine в except-блоках и
    самостоятельно преобразует их в протокольные ответы.

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
    # Регистрация маршрутов
    # ─────────────────────────────────────────────────────────────────────

    def route(self, action_class: type[BaseAction[Any, Any]]) -> B:
        """
        Начинает регистрацию маршрута для указанного класса действия.

        Создаёт fluent-builder через ``_create_builder()`` и возвращает его.
        Разработчик настраивает builder через цепочку вызовов и завершает
        ``register()``, который создаёт конкретный RouteRecord и добавляет
        его в ``_routes``.

        Аргументы:
            action_class: класс действия (наследник BaseAction).
                          Не экземпляр — именно класс. Экземпляр создаётся
                          адаптером при каждом входящем запросе.

        Возвращает:
            B — fluent-builder конкретного протокола.

        Исключения:
            TypeError: если action_class не является классом.
            TypeError: если action_class не наследует BaseAction.
        """
        if not isinstance(action_class, type):
            raise TypeError(
                f"route() ожидает класс (type), "
                f"получен {type(action_class).__name__}: {action_class!r}."
            )

        if not issubclass(action_class, BaseAction):
            raise TypeError(
                f"route() ожидает наследника BaseAction, "
                f"получен {action_class.__name__}. "
                f"Класс должен наследовать BaseAction."
            )

        return self._create_builder(action_class)

    def _add_route(self, record: R) -> None:
        """
        Добавляет RouteRecord в список маршрутов.

        Вызывается из fluent-builder при ``register()``.

        Аргументы:
            record: конфигурация маршрута — конкретный наследник
                    BaseRouteRecord, собранный builder-ом.
        """
        self._routes.append(record)

    # ─────────────────────────────────────────────────────────────────────
    # Абстрактные методы
    # ─────────────────────────────────────────────────────────────────────

    @abstractmethod
    def _create_builder(self, action_class: type[BaseAction[Any, Any]]) -> B:
        """
        Создаёт fluent-builder для указанного класса действия.

        Абстрактный метод. Каждый конкретный адаптер реализует его,
        возвращая свой протокольно-специфичный builder.

        Аргументы:
            action_class: класс действия (уже проверен в route()).

        Возвращает:
            B — экземпляр fluent-builder конкретного протокола.
        """

    @abstractmethod
    def build(self) -> Any:
        """
        Создаёт протокольное приложение из зарегистрированных маршрутов.

        Абстрактный метод. Каждый конкретный адаптер реализует его,
        обходя ``_routes`` и генерируя протокольные эндпоинты.

        Возвращает:
            Протокольное приложение. Тип определяется конкретным адаптером.
        """
