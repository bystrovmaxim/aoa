# src/action_machine/auth/no_auth_coordinator.py
"""
NoAuthCoordinator — провайдер аутентификации для открытых API.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

NoAuthCoordinator — явная реализация AuthCoordinator, которая создаёт
анонимный Context для каждого запроса. Используется для API, не требующих
аутентификации: публичные сервисы, примеры, health check эндпоинты.

Разработчик не может «забыть» подключить аутентификацию — параметр
auth_coordinator обязателен в BaseAdapter. Для открытых API разработчик
осознанно передаёт NoAuthCoordinator(), явно декларируя отсутствие
аутентификации в коде.

═══════════════════════════════════════════════════════════════════════════════
АНОНИМНЫЙ CONTEXT
═══════════════════════════════════════════════════════════════════════════════

NoAuthCoordinator.process() всегда возвращает Context с:
- user: UserInfo(user_id=None, roles=[]) — анонимный пользователь.
- request: пустой RequestInfo.
- runtime: пустой RuntimeInfo.

Это гарантирует, что ActionProductMachine._check_action_roles() работает
корректно: действия с @CheckRoles(CheckRoles.NONE) проходят проверку,
действия с конкретными ролями — отклоняются с AuthorizationError.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth.no_auth_coordinator import NoAuthCoordinator
    from action_machine.contrib.fastapi import FastApiAdapter

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

    # Для MCP:
    adapter = McpAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )
"""

from typing import Any

from action_machine.context.context import Context


class NoAuthCoordinator:
    """
    Провайдер аутентификации для открытых API.

    Всегда возвращает анонимный Context без пользователя и ролей.
    Используется для явной декларации отсутствия аутентификации.

    Реализует тот же интерфейс, что и AuthCoordinator:
    асинхронный метод process(request_data) → Context.
    """

    async def process(self, request_data: Any) -> Context:
        """
        Создаёт анонимный Context для каждого запроса.

        Не выполняет никаких проверок. Всегда возвращает Context
        с пустым UserInfo (user_id=None, roles=[]).

        Аргументы:
            request_data: данные запроса (игнорируются).

        Возвращает:
            Context — анонимный контекст выполнения.
        """
        return Context()
