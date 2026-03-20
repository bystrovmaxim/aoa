# src/action_machine/Core/AspectMethod.py

"""
Протокол аспектных методов и декораторы для их объявления.

ВНИМАНИЕ: Старые декораторы aspect_old и summary_aspect_old удалены.
Для определения аспектов используйте regular_aspect и summary_aspect
из пакета action_machine.aspects.

Содержит:
- depends() — декоратор для объявления зависимостей действия.
- connection() — декоратор для объявления соединений, необходимых действию.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ..ResourceManagers.BaseResourceManager import BaseResourceManager

if TYPE_CHECKING:
    pass


def depends(
    klass: type[Any],
    *,
    description: str = "",
    factory: Callable[[], Any] | None = None,
) -> Callable[[type[Any]], type[Any]]:
    """
    Декоратор для объявления зависимости действия от любого класса.

    Может использоваться несколько раз для одного действия.
    Создаёт новый список зависимостей для каждого класса (не мутирует родительский).

    Аргументы:
        klass: класс зависимости (может быть Action, сервис, репозиторий и т.д.)
        description: описание зависимости (для документации).
        factory: опциональная фабрика для создания экземпляра.
            Если не указана, используется конструктор по умолчанию.

    Возвращает:
        Декоратор, который добавляет информацию о зависимости в атрибут _dependencies.
    """

    def decorator(cls: type[Any]) -> type[Any]:
        # Создаём НОВЫЙ список, копируя родительский (если есть)
        deps = list(getattr(cls, "_dependencies", []))
        deps.append(
            {
                "class": klass,
                "description": description,
                "factory": factory,
            }
        )
        cls._dependencies = deps
        return cls

    return decorator


def connection(
    key: str,
    klass: type[BaseResourceManager],
    *,
    description: str = "",
) -> Callable[[type[Any]], type[Any]]:
    """
    Декоратор для объявления соединения, необходимого действию.

    Используется на уровне класса действия для декларации того,
    какие ресурсные менеджеры (соединения) ожидает действие.
    ActionMachine проверяет соответствие переданных connections
    и объявленных через @connection перед выполнением аспектов.

    Может использоваться несколько раз для одного действия (несколько соединений).
    Создаёт новый список соединений для каждого класса (не мутирует родительский).

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