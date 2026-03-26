# src/action_machine/ResourceManagers/connection.py
"""
Декоратор @connection — объявление подключения к внешнему ресурсу.

Назначение:
    Декоратор @connection — часть грамматики намерений ActionMachine. Он объявляет,
    что действие использует внешний ресурс (база данных, очередь сообщений,
    HTTP-клиент и т.д.), управляемый через ResourceManager. Машина
    (ActionProductMachine) при запуске действия создаёт менеджеры ресурсов,
    открывает соединения и передаёт их в аспекты через параметр connections.

    Каждое соединение идентифицируется строковым ключом (key), по которому
    аспект обращается к нему: connections["db"], connections["redis"].

Ограничения (инварианты):
    - Применяется только к классам, не к функциям, методам или свойствам.
    - Класс должен наследовать ConnectionGateHost — миксин, разрешающий @connection.
    - klass должен быть подклассом BaseResourceManager.
    - key должен быть непустой строкой.
    - Дублирование ключей в одном классе запрещено.

Наследование:
    При первом применении @connection к подклассу декоратор копирует
    родительский список _connection_info в собственный __dict__. Дочерний
    класс наследует соединения родителя, но добавление новых не мутирует
    родительский список.

Пример:
    @connection(PostgresManager, key="db", description="Основная БД")
    @connection(RedisManager, key="cache", description="Кэш")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Загрузка данных")
        async def load_data(self, params, state, box, connections):
            db = connections["db"]
            result = await db.execute("SELECT ...")
            return {"data": result}

Ошибки:
    TypeError — klass не подкласс BaseResourceManager; декоратор применён
               не к классу; класс не наследует ConnectionGateHost;
               key не строка.
    ValueError — key пустая строка; дублирование ключа.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


@dataclass(frozen=True)
class ConnectionInfo:
    """
    Неизменяемая запись об одном подключении к внешнему ресурсу.

    Атрибуты:
        cls: класс менеджера ресурсов (подкласс BaseResourceManager).
        key: строковый ключ для доступа из аспекта через connections[key].
        description: человекочитаемое описание подключения.
    """
    cls: type
    key: str
    description: str = ""


def connection(klass: Any, *, key: str, description: str = ""):
    """
    Декоратор уровня класса. Объявляет подключение к внешнему ресурсу.

    Аргументы:
        klass: класс менеджера ресурсов. Должен быть подклассом BaseResourceManager.
        key: строковый ключ для идентификации соединения. Непустая строка.
        description: описание подключения для документации и интроспекции.

    Возвращает:
        Декоратор, который добавляет ConnectionInfo в cls._connection_info.

    Исключения:
        TypeError:
            - klass не является классом (type).
            - klass не подкласс BaseResourceManager.
            - key не строка.
            - description не строка.
            - Декоратор применён не к классу.
            - Класс не наследует ConnectionGateHost.
        ValueError:
            - key пустая строка.
            - Ключ key уже объявлен для этого класса.
    """
    # ── Проверка аргументов декоратора (выполняется при @connection(...)) ──

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

    def decorator(cls: Any) -> Any:
        # ── Проверка цели декоратора ──

        # Цель — класс
        if not isinstance(cls, type):
            raise TypeError(
                f"@connection можно применять только к классу. "
                f"Получен объект типа {type(cls).__name__}: {cls!r}."
            )

        # Класс содержит миксин ConnectionGateHost
        from action_machine.ResourceManagers.connection_gate_host import ConnectionGateHost

        if not issubclass(cls, ConnectionGateHost):
            raise TypeError(
                f"@connection(key=\"{key}\") применён к классу {cls.__name__}, "
                f"который не наследует ConnectionGateHost. "
                f"Добавьте ConnectionGateHost в цепочку наследования."
            )

        # Создаём собственный список соединений для этого класса
        if '_connection_info' not in cls.__dict__:
            cls._connection_info = list(getattr(cls, '_connection_info', []))

        # Проверка дубликатов ключей
        if any(info.key == key for info in cls._connection_info):
            raise ValueError(
                f"@connection(key=\"{key}\"): ключ \"{key}\" уже объявлен "
                f"для класса {cls.__name__}. Каждый ключ должен быть уникальным."
            )

        # Регистрация соединения
        cls._connection_info.append(
            ConnectionInfo(cls=klass, key=key, description=description)
        )

        return cls

    return decorator
