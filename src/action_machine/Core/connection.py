"""
Декоратор @connection для объявления соединений, необходимых действию.

Используется на уровне класса действия для декларации того,
какие ресурсные менеджеры (соединения) ожидает действие.
ActionMachine проверяет соответствие переданных connections
и объявленных через @connection перед выполнением аспектов.

Может использоваться несколько раз для одного действия (несколько соединений).
Создаёт новый список соединений для каждого класса (не мутирует родительский).

В будущем будет заменён на ConnectionGate и ConnectionGateHost,
но пока остаётся для обратной совместимости.
"""

from collections.abc import Callable
from typing import Any

from ..ResourceManagers.BaseResourceManager import BaseResourceManager


def connection(
    key: str,
    klass: type[BaseResourceManager],
    *,
    description: str = "",
) -> Callable[[type[Any]], type[Any]]:
    """
    Декоратор для объявления соединения, необходимого действию.

    Аргументы:
        key: строковое имя ключа в словаре connections (и в TypedDict).
            Например: "connection", "cache", "analytics_db".
        klass: класс ресурсного менеджера (наследник BaseResourceManager).
        description: описание соединения (для документации).

    Возвращает:
        Декоратор, который добавляет информацию о соединении в атрибут _connections.

    Пример:
        @connection("connection", PostgresConnectionManager, description="Основная БД")
        @connection("cache", RedisConnectionManager, description="Кеш")
        class MyAction(BaseAction[...]):
            ...

        # В аспектах доступно:
        #   connections["connection"]  — PostgresConnectionManager (или прокси)
        #   connections["cache"]       — RedisConnectionManager (или прокси)
    """

    def decorator(cls: type[Any]) -> type[Any]:
        # Создаём НОВЫЙ список, копируя родительский (если есть)
        conns = list(getattr(cls, "_connections", []))
        conns.append(
            {
                "key": key,
                "class": klass,
                "description": description,
            }
        )
        cls._connections = conns
        return cls

    return decorator