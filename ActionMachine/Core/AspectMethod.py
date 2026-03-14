################################################################################
# Файл: ActionMachine/Core/AspectMethod.py
################################################################################

# ActionMachine/Core/AspectMethod.py
"""
Протокол аспектных методов и декораторы для их объявления.

Содержит:
- AspectMethod — протокол, описывающий методы с атрибутами аспектов.
- aspect() — декоратор для обычных аспектов.
- summary_aspect() — декоратор для главного (summary) аспекта.
- depends() — декоратор для объявления зависимостей действия.
- connection() — декоратор для объявления соединений, необходимых действию.
"""

import inspect
from typing import Any, Callable, Optional, Protocol, Type, runtime_checkable, cast


@runtime_checkable
class AspectMethod(Protocol):
    """
    Протокол, описывающий методы, помеченные декораторами aspect/summary_aspect.

    Атрибуты:
        _is_aspect: флаг, что метод является аспектом.
        _aspect_description: текстовое описание аспекта.
        _aspect_type: тип аспекта ('regular' или 'summary').
        __code__: объект кода (для сортировки по номеру строки).
        __name__: имя метода.
        __qualname__: квалифицированное имя метода.
        __call__: сигнатура вызова метода.
    """

    _is_aspect: bool
    _aspect_description: str
    _aspect_type: str
    __code__: Any
    __name__: str
    __qualname__: str
    __call__: Callable[..., Any]


def aspect(description: str) -> Callable[[Callable[..., Any]], AspectMethod]:
    """
    Декоратор для обычных аспектов.

    Помечает метод как регулярный аспект, который выполняется перед summary.
    Метод должен быть асинхронным (async def) и принимать
    (self, params, state, deps, connections) и возвращать dict.

    Аргументы:
        description: текстовое описание аспекта (для документации и логирования).

    Возвращает:
        Декоратор, который добавляет атрибуты аспекта к методу.

    Исключения:
        TypeError: если метод не является корутиной.
    """
    def decorator(method: Callable[..., Any]) -> AspectMethod:
        if not inspect.iscoroutinefunction(method):
            raise TypeError(
                f"Аспект '{method.__name__}' должен быть async def. "
                "В AOA все аспекты асинхронные."
            )
        method._is_aspect = True                      # type: ignore[attr-defined]
        method._aspect_description = description       # type: ignore[attr-defined]
        method._aspect_type = 'regular'                # type: ignore[attr-defined]
        return cast(AspectMethod, method)
    return decorator


def summary_aspect(description: str) -> Callable[[Callable[..., Any]], AspectMethod]:
    """
    Декоратор для главного аспекта (должен быть ровно один в каждом действии).

    Summary-аспект выполняется последним и возвращает итоговый Result.
    Должен быть асинхронным (async def).
    Метод принимает (self, params, state, deps, connections).

    Аргументы:
        description: текстовое описание аспекта (для документации и логирования).

    Возвращает:
        Декоратор, который добавляет атрибуты summary-аспекта к методу.

    Исключения:
        TypeError: если метод не является корутиной.
    """
    def decorator(method: Callable[..., Any]) -> AspectMethod:
        if not inspect.iscoroutinefunction(method):
            raise TypeError(
                f"Summary-аспект '{method.__name__}' должен быть async def. "
                "В AOA все аспекты асинхронные."
            )
        method._is_aspect = True                      # type: ignore[attr-defined]
        method._aspect_description = description       # type: ignore[attr-defined]
        method._aspect_type = 'summary'                # type: ignore[attr-defined]
        return cast(AspectMethod, method)
    return decorator


def depends(
    klass: Type[Any],
    *,
    description: str = "",
    factory: Optional[Callable[[], Any]] = None,
) -> Callable[[Type[Any]], Type[Any]]:
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
    def decorator(cls: Type[Any]) -> Type[Any]:
        # Создаём НОВЫЙ список, копируя родительский (если есть)
        deps = list(getattr(cls, '_dependencies', []))
        deps.append({
            'class': klass,
            'description': description,
            'factory': factory,
        })
        cls._dependencies = deps
        return cls
    return decorator


def connection(
    key: str,
    klass: Type[Any],
    *,
    description: str = "",
) -> Callable[[Type[Any]], Type[Any]]:
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
    def decorator(cls: Type[Any]) -> Type[Any]:
        # Создаём НОВЫЙ список, копируя родительский (если есть)
        conns = list(getattr(cls, '_connections', []))
        conns.append({
            'key': key,
            'class': klass,
            'description': description,
        })
        cls._connections = conns
        return cls
    return decorator

################################################################################