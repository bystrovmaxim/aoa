"""
Декоратор @connection для объявления соединений, необходимых действию.

Используется на уровне класса действия для декларации того,
какие ресурсные менеджеры (соединения) ожидает действие.
ActionMachine проверяет соответствие переданных connections
и объявленных через @connection перед выполнением аспектов.

Может использоваться несколько раз для одного действия (несколько соединений).

Архитектурная роль:
    Декоратор добавляет информацию о соединениях в атрибут `_connection_info`,
    объявленный в миксине `ConnectionGateHost`. При первом вызове
    `get_connection_gate()` хост собирает `_connection_info`, регистрирует
    каждое соединение в `ConnectionGate` и замораживает шлюз.

    Имя `_connection_info` (с одним подчёркиванием) используется, чтобы избежать
    Python name mangling и обеспечить доступность в дочерних классах.

    Декоратор проверяет, что целевой класс наследует ConnectionGateHost.
    Если нет — выбрасывает TypeError. Это гарантирует, что декоратор
    не добавляет динамических атрибутов — все поля объявлены в миксине.
"""

from collections.abc import Callable
from typing import Any

from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager
from action_machine.ResourceManagers.connection_gate import ConnectionInfo
from action_machine.ResourceManagers.connection_gate_host import ConnectionGateHost


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
        Декоратор, который добавляет информацию о соединении в класс.

    Исключения:
        TypeError: если класс не наследует ConnectionGateHost.

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
        # Проверяем, что класс наследует ConnectionGateHost,
        # который объявляет атрибут _connection_info как ClassVar.
        if not issubclass(cls, ConnectionGateHost):
            raise TypeError(
                f"@connection can only be applied to classes inheriting ConnectionGateHost. "
                f"Class {cls.__name__} does not inherit ConnectionGateHost. "
                f"Ensure the class inherits from BaseAction or ConnectionGateHost directly."
            )

        # _connection_info объявлен в ConnectionGateHost как ClassVar[list[ConnectionInfo] | None],
        # поэтому после issubclass-проверки mypy знает о его существовании.
        if cls._connection_info is None:
            cls._connection_info = []
        else:
            # Создаём копию, чтобы не мутировать родительский список
            cls._connection_info = list(cls._connection_info)

        cls._connection_info.append(
            ConnectionInfo(
                key=key,
                klass=klass,
                description=description,
            )
        )

        return cls

    return decorator