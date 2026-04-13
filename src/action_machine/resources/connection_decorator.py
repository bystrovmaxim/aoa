# src/action_machine/resources/connection_decorator.py
"""
Декоратор @connection — объявление подключения к внешнему ресурсу.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @connection — часть грамматики намерений ActionMachine. Он объявляет,
что действие использует внешний ресурс (база данных, очередь сообщений,
HTTP-клиент и т.д.), управляемый через ResourceManager. Машина
(ActionProductMachine) при запуске действия проверяет соответствие
объявленных и фактически переданных соединений, затем передаёт их
в аспекты через параметр connections.

Каждое соединение идентифицируется строковым ключом (key), по которому
аспект обращается к нему: connections["db"], connections["redis"].

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @connection(PostgresManager, key="db", description="Основная БД")
        │
        ▼  Декоратор записывает в cls._connection_info
    ConnectionInfo(cls=PostgresManager, key="db", description="Основная БД")
        │
        ▼  ConnectionIntentInspector reads _connection_info
    get_connections(cls) → (ConnectionInfo(...), ...)
        │
        ▼  ActionProductMachine._check_connections(action, connections, metadata)
    Сравнивает объявленные ключи (facet snapshot ``connections``) с фактическими
        │
        ▼  Аспекты получают connections["db"] — экземпляр PostgresManager

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к классам, не к функциям, методам или свойствам.
- Класс должен наследовать ConnectionIntent — миксин, разрешающий @connection.
- klass должен быть подклассом BaseResourceManager.
- key должен быть непустой строкой.
- description должен быть строкой.
- Дублирование ключей в одном классе запрещено.

═══════════════════════════════════════════════════════════════════════════════
НАСЛЕДОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

При первом применении @connection к подклассу декоратор копирует
родительский список _connection_info в собственный __dict__. Дочерний
класс наследует соединения родителя, но добавление новых не мутирует
родительский список.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    @connection(PostgresManager, key="db", description="Основная БД")
    @connection(RedisManager, key="cache", description="Кэш")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Загрузка данных")
        async def load_data(self, params, state, box, connections):
            db = connections["db"]
            result = await db.execute("SELECT ...")
            return {"data": result}

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — klass не подкласс BaseResourceManager; декоратор применён
               не к классу; класс не наследует ConnectionIntent;
               key не строка; description не строка.
    ValueError — key пустая строка; дублирование ключа.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.connection_intent import ConnectionIntent

# ═════════════════════════════════════════════════════════════════════════════
# Датакласс для хранения информации о соединении
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ConnectionInfo:
    """
    Immutable record for one declared resource connection.

    Created by ``@connection`` and stored on ``cls._connection_info``.
    ``ConnectionIntentInspector`` builds the coordinator facet; the machine
    compares keys from the ``connections`` facet snapshot to the runtime
    ``connections`` mapping passed into ``run``.

    Attributes:
        cls: ``BaseResourceManager`` subclass (resource type).
        key: Non-empty string key for ``connections[key]`` inside aspects.
        description: Human-readable label for introspection and docs.
    """
    cls: type
    key: str
    description: str = ""


# ═════════════════════════════════════════════════════════════════════════════
# Валидация аргументов декоратора (вынесена для снижения сложности C901)
# ═════════════════════════════════════════════════════════════════════════════


def _validate_connection_args(klass: Any, key: str, description: str) -> None:
    """
    Проверяет корректность аргументов декоратора @connection.

    Вызывается один раз при создании декоратора (до применения к классу).
    Выбрасывает TypeError или ValueError при нарушении контракта.

    Проверки:
    1. klass — класс (type), не экземпляр и не строка.
    2. klass — подкласс BaseResourceManager.
    3. key — строка (str).
    4. key — непустая строка (после strip).
    5. description — строка (str).

    Аргументы:
        klass: класс менеджера ресурсов.
        key: строковый ключ соединения.
        description: описание соединения.

    Исключения:
        TypeError: если тип аргумента не соответствует ожидаемому.
        ValueError: если key — пустая строка.
    """
    if not isinstance(klass, type):
        raise TypeError(
            f"@connection ожидает класс, получен {type(klass).__name__}: {klass!r}. "
            f"Передайте класс менеджера ресурсов."
        )

    if not issubclass(klass, BaseResourceManager):
        raise TypeError(
            f"@connection: класс {klass.__name__} не является подклассом "
            f"BaseResourceManager. Менеджер ресурсов должен наследовать "
            f"BaseResourceManager."
        )

    if not isinstance(key, str):
        raise TypeError(
            f"@connection: параметр key должен быть строкой, "
            f"получен {type(key).__name__}: {key!r}."
        )

    if not key.strip():
        raise ValueError(
            "@connection: key не может быть пустой строкой. "
            "Укажите ключ для идентификации соединения, например 'db'."
        )

    if not isinstance(description, str):
        raise TypeError(
            f"@connection: параметр description должен быть строкой, "
            f"получен {type(description).__name__}."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Основной декоратор
# ═════════════════════════════════════════════════════════════════════════════


def connection(klass: Any, *, key: str, description: str = "") -> Callable[[type], type]:
    """
    Декоратор уровня класса. Объявляет подключение к внешнему ресурсу.

    Записывает ConnectionInfo в атрибут cls._connection_info целевого класса.
    При первом применении к подклассу копирует родительский список,
    чтобы не мутировать его.

    Аргументы:
        klass: класс менеджера ресурсов. Должен быть подклассом BaseResourceManager.
               Примеры: PostgresConnectionManager, RedisManager.
        key: строковый ключ для идентификации соединения. Непустая строка.
             Используется в аспектах: connections["db"], connections["cache"].
        description: описание подключения для документации и интроспекции.
                     По умолчанию пустая строка.

    Возвращает:
        Декоратор, который добавляет ConnectionInfo в cls._connection_info
        и возвращает класс без изменений.

    Исключения:
        TypeError:
            - klass не является классом (type).
            - klass не подкласс BaseResourceManager.
            - key не строка.
            - description не строка.
            - Декоратор применён не к классу.
            - Класс не наследует ConnectionIntent.
        ValueError:
            - key пустая строка.
            - Ключ key уже объявлен для этого класса.

    Пример:
        @connection(PostgresManager, key="db", description="Основная БД")
        @connection(RedisManager, key="cache", description="Кэш")
        class MyAction(BaseAction[MyParams, MyResult]):
            ...
    """
    # ── Проверка аргументов (делегирована в отдельную функцию) ──
    _validate_connection_args(klass, key, description)

    def decorator(cls: Any) -> Any:
        """
        Внутренний декоратор, применяемый к целевому классу.

        Проверяет:
        1. cls — класс (type), не функция/метод/свойство.
        2. cls наследует ConnectionIntent.
        3. Ключ key не дублируется в _connection_info.

        Затем добавляет ConnectionInfo в cls._connection_info.
        """
        # ── Проверка цели декоратора ──

        # Цель — класс
        if not isinstance(cls, type):
            raise TypeError(
                f"@connection можно применять только к классу. "
                f"Получен объект типа {type(cls).__name__}: {cls!r}."
            )

        # Класс наследует ConnectionIntent
        if not issubclass(cls, ConnectionIntent):
            raise TypeError(
                f"@connection(key=\"{key}\") применён к классу {cls.__name__}, "
                f"который не наследует ConnectionIntent. "
                f"Добавьте ConnectionIntent в цепочку наследования."
            )

        # ── Создание собственного списка соединений ──
        # При первом применении @connection к подклассу копируем родительский
        # список, чтобы дочерний класс не мутировал список родителя.
        if '_connection_info' not in cls.__dict__:
            cls._connection_info = list(getattr(cls, '_connection_info', []))

        # ── Проверка дубликатов ключей ──
        if any(info.key == key for info in cls._connection_info):
            raise ValueError(
                f"@connection(key=\"{key}\"): ключ \"{key}\" уже объявлен "
                f"для класса {cls.__name__}. Каждый ключ должен быть уникальным."
            )

        # ── Регистрация соединения ──
        cls._connection_info.append(
            ConnectionInfo(cls=klass, key=key, description=description)
        )

        return cls

    return decorator
