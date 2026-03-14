################################################################################
# Файл: ActionMachine/ResourceManagers/Connections.py
################################################################################

# ActionMachine/ResourceManagers/Connections.py
"""
Базовый TypedDict для словаря connections, передаваемого в аспекты.

В 99% случаев действию нужно одно соединение, поэтому базовый TypedDict
содержит единственный стандартный ключ 'connection'. Если действию требуется
больше соединений, разработчик создаёт наследника с дополнительными ключами.

TypedDict используется с total=False, потому что:
- не все действия используют все ключи;
- набор ключей определяется декораторами @connection на уровне класса действия;
- машина гарантирует точное соответствие переданных ключей объявленным.

TypedDict — это статический контракт для IDE и mypy.
В runtime connections остаётся обычным dict, и ActionMachine
проверяет его содержимое через _check_connections() динамически.

Пример использования (простой случай — 99%):

    @connection("connection", PostgresConnectionManager, description="Основная БД")
    @CheckRoles(CheckRoles.ANY, desc="...")
    class MyAction(BaseAction[...]):

        @aspect("Загрузка")
        async def load(self, params, state, deps, connections: Connections) -> ...:
            conn = connections["connection"]
            ...

Пример использования (сложный случай — наследование):

    class MyConnections(Connections, total=False):
        cache: BaseResourceManager
        analytics_db: BaseResourceManager

    @connection("connection", PostgresConnectionManager, description="Основная БД")
    @connection("cache", RedisConnectionManager, description="Кеш")
    @connection("analytics_db", PostgresConnectionManager, description="Аналитика")
    class ComplexAction(BaseAction[...]):

        @aspect("Загрузка")
        async def load(self, params, state, deps, connections: MyConnections) -> ...:
            db = connections["connection"]
            cache = connections["cache"]
            ...
"""

from typing import TypedDict
from ActionMachine.ResourceManagers.BaseResourceManager import BaseResourceManager


class Connections(TypedDict, total=False):
    """
    Базовый TypedDict для connections.

    Содержит один стандартный ключ 'connection', покрывающий 99% случаев.
    Для дополнительных соединений создавайте наследника с total=False.

    Ключи:
        connection: основной ресурсный менеджер (соединение с БД, кеш и т.д.)
    """
    connection: BaseResourceManager

################################################################################