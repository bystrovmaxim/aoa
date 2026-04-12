# src/action_machine/resource_managers/connection_intent.py
"""
Модуль: ConnectionIntent — маркерный миксин для декоратора @connection.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ConnectionIntent — миксин-маркер, который разрешает применение декоратора
@connection к классу. Декоратор при применении проверяет:

    if not issubclass(cls, ConnectionIntent):
        raise TypeError("Класс должен наследовать ConnectionIntent")

Без наследования от ConnectionIntent декоратор @connection выбросит
TypeError. Это защита от случайного объявления соединений на классах,
которые не поддерживают работу с ресурс-менеджерами.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        RoleIntent,
        DependencyIntent[object],
        CheckerIntent,
        AspectIntent,
        ConnectionIntent,             ← маркер: разрешает @connection
    ): ...

    @connection(PostgresManager, key="db", description="Основная БД")
    @connection(RedisManager, key="cache", description="Кеш")
    class DataAction(BaseAction[P, R]):
        ...

    # Декоратор @connection проверяет:
    #   1. issubclass(DataAction, ConnectionIntent) → True → OK
    #   2. issubclass(PostgresManager, BaseResourceManager) → True → OK
    #   3. key="db" — непустая строка → OK
    #   4. Дубликатов по ключу нет → OK
    #   5. Записывает ConnectionInfo в cls._connection_info

    # ConnectionIntentInspector читает cls._connection_info при build().

    # ActionProductMachine: ключи из facet-снимка connections (GateCoordinator).

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # BaseAction уже наследует ConnectionIntent — любой Action
    # поддерживает @connection автоматически:

    @connection(PostgresManager, key="db", description="Основная БД")
    class UserAction(BaseAction[UserParams, UserResult]):
        @regular_aspect("Загрузка пользователя")
        async def load_user(self, params, state, box, connections):
            db = connections["db"]
            user = await db.fetch_one(...)
            return {"user": user}

        @summary_aspect("Результат")
        async def result(self, params, state, box, connections):
            return UserResult(user=state["user"])
"""

from typing import Any, ClassVar


class ConnectionIntent:
    """
    Маркерный миксин, разрешающий использование декоратора @connection.

    Класс, НЕ наследующий ConnectionIntent, не может быть целью
    @connection — декоратор выбросит TypeError при попытке применения.

    Миксин не содержит логики, полей или методов. Его единственная функция —
    служить проверочным маркером для issubclass().

    Атрибуты уровня класса (создаются динамически декоратором):
        _connection_info : list[ConnectionInfo]
            Список объектов ConnectionInfo(cls, key, description),
            записываемый декоратором @connection. Читается инспектором
            соединений при ``GateCoordinator.build()``.
    """

    # Аннотация для mypy, чтобы он не ругался на динамический атрибут
    _connection_info: ClassVar[list[Any]]
