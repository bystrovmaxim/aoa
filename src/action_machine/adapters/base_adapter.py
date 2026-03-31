# src/action_machine/adapters/base_adapter.py
"""
BaseAdapter[R] — абстрактный базовый класс для всех протокольных адаптеров.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseAdapter — единый контракт для адаптеров, преобразующих внешние протоколы
(HTTP, MCP, gRPC, CLI) в вызовы ``machine.run(context, action, params, connections)``.

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНАЯ АУТЕНТИФИКАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

Параметр auth_coordinator обязателен. Разработчик не может «забыть»
подключить аутентификацию — это ошибка конструктора (TypeError), а не
молчаливый баг в production.

Для открытых API используется NoAuthCoordinator — явная декларация
отсутствия аутентификации:

    from action_machine.auth.no_auth_coordinator import NoAuthCoordinator

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

NoAuthCoordinator реализует тот же интерфейс, что и AuthCoordinator:
асинхронный метод process(request_data) → Context. Всегда возвращает
анонимный Context с пустым UserInfo (user_id=None, roles=[]).

═══════════════════════════════════════════════════════════════════════════════
КОНВЕНЦИЯ ИМЕНОВАНИЯ МАППЕРОВ
═══════════════════════════════════════════════════════════════════════════════

    params_mapper   → возвращает params   (преобразует request → params)
    response_mapper → возвращает response (преобразует result  → response)

═══════════════════════════════════════════════════════════════════════════════
FLUENT API
═══════════════════════════════════════════════════════════════════════════════

Метод ``_add_route(record)`` возвращает ``self``, что позволяет конкретным
адаптерам строить цепочки через ``return self._add_route(record)``
в протокольных методах (post, get, tool и т.д.).

Метод ``build()`` завершает цепочку и возвращает протокольное приложение.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────┐
    │  BaseAdapter[R]                      │
    │                                      │
    │  machine: ActionProductMachine       │
    │  auth_coordinator: Any (обязат.)     │
    │  connections_factory: Fn | None      │
    │  _routes: list[R]                    │
    │                                      │
    │  _add_route(record: R) → Self        │
    │  build() → Any                       │
    └──────────────────────────────────────┘
               ▲
    ┌──────────┴──────────────────────────┐
    │  FastAPIAdapter                      │
    │  MCPAdapter                          │
    └──────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # С аутентификацией:
    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=AuthCoordinator(extractor, authenticator, assembler),
    )

    # Без аутентификации (явная декларация):
    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

    # MCP-адаптер:
    adapter = McpAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Self

from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .base_route_record import BaseRouteRecord


class BaseAdapter[R: BaseRouteRecord](ABC):
    """
    Абстрактный базовый класс для всех протокольных адаптеров ActionMachine.

    Параметр auth_coordinator обязателен. Для открытых API используется
    NoAuthCoordinator — явная декларация отсутствия аутентификации.

    Атрибуты:
        _machine : ActionProductMachine
            Машина выполнения действий.

        _auth_coordinator : Any
            Координатор аутентификации. AuthCoordinator или NoAuthCoordinator.
            Обязательный параметр — не может быть None.

        _connections_factory : Callable[..., dict[str, BaseResourceManager]] | None
            Фабрика соединений.

        _routes : list[R]
            Список зарегистрированных маршрутов.
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
    ) -> None:
        """
        Инициализирует адаптер.

        Аргументы:
            machine: машина выполнения действий. Обязательный параметр.
                     Должен быть экземпляром ActionProductMachine.
            auth_coordinator: координатор аутентификации. Обязательный параметр.
                              Для открытых API используйте NoAuthCoordinator().
                              None не допускается — TypeError.
            connections_factory: фабрика соединений. Если None —
                                 connections не передаются.

        Исключения:
            TypeError: если machine не ActionProductMachine.
            TypeError: если auth_coordinator равен None.
        """
        if not isinstance(machine, ActionProductMachine):
            raise TypeError(
                f"BaseAdapter ожидает ActionProductMachine, "
                f"получен {type(machine).__name__}: {machine!r}."
            )

        if auth_coordinator is None:
            raise TypeError(
                "auth_coordinator обязателен. Передайте AuthCoordinator "
                "для аутентификации или NoAuthCoordinator() для открытых API. "
                "Пример: adapter = FastApiAdapter(machine=machine, "
                "auth_coordinator=NoAuthCoordinator())"
            )

        self._machine: ActionProductMachine = machine
        self._auth_coordinator: Any = auth_coordinator
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
    def auth_coordinator(self) -> Any:
        """Возвращает координатор аутентификации."""
        return self._auth_coordinator

    @property
    def connections_factory(self) -> Callable[..., dict[str, BaseResourceManager]] | None:
        """Возвращает фабрику соединений (или None)."""
        return self._connections_factory

    @property
    def routes(self) -> list[R]:
        """Возвращает список зарегистрированных маршрутов."""
        return self._routes

    # ─────────────────────────────────────────────────────────────────────
    # Внутренний метод регистрации (fluent)
    # ─────────────────────────────────────────────────────────────────────

    def _add_route(self, record: R) -> Self:
        """
        Добавляет RouteRecord в список маршрутов и возвращает self.

        Возврат self обеспечивает fluent API.
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

        Возвращает:
            Протокольное приложение:
            - FastAPIAdapter.build() → FastAPI
            - MCPAdapter.build() → FastMCP
        """
