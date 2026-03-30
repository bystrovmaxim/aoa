# src/action_machine/resource_managers/base_resource_manager.py
"""
Базовый абстрактный класс для всех ресурсных менеджеров.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Ресурсный менеджер — это любой объект, управляющий внешним ресурсом
(соединение с БД, кеш, очередь сообщений и т.д.), который передаётся
в аспекты действий через словарь connections.

Каждый ресурсный менеджер должен уметь возвращать класс-обёртку (wrapper),
который используется при передаче ресурса в дочерние действия.
Обёртка запрещает управление жизненным циклом ресурса (open/commit/rollback),
но разрешает выполнение запросов (execute).

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНЫЙ ДЕКОРАТОР @meta
═══════════════════════════════════════════════════════════════════════════════

Каждый ресурсный менеджер обязан иметь декоратор @meta с описанием.
Контролируется ResourceMetaGateHost, который входит в цепочку наследования
BaseResourceManager. MetadataBuilder при сборке проверяет: если класс
наследует ResourceMetaGateHost — @meta обязателен. Без него — TypeError.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseResourceManager(ABC, ResourceMetaGateHost):
        ...                             ← маркер: @meta обязателен

    @meta(description="Менеджер соединений с PostgreSQL")
    class PostgresConnectionManager(IConnectionManager):
        ...

    @meta(description="Менеджер Redis-кеша", domain=CacheDomain)
    class RedisManager(BaseResourceManager):
        ...

    # Без @meta — ошибка при сборке метаданных:
    class BadManager(BaseResourceManager):
        ...
    # MetadataBuilder.build(BadManager) → TypeError:
    # "Ресурсный менеджер BadManager не имеет декоратора @meta.
    #  Добавьте @meta(description=\"...\")."

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    @meta(description="Менеджер соединений с PostgreSQL")
    class PostgresConnectionManager(IConnectionManager):
        def __init__(self, connection_params: dict[str, Any]):
            self._connection_params = connection_params
            self._conn = None

        async def open(self) -> None:
            self._conn = await asyncpg.connect(**self._connection_params)

        async def commit(self) -> None:
            await self._conn.execute("COMMIT")

        async def rollback(self) -> None:
            await self._conn.execute("ROLLBACK")

        async def execute(self, query: str, params=None) -> Any:
            return await self._conn.execute(query, *params if params else ())

        def get_wrapper_class(self) -> type[IConnectionManager] | None:
            return WrapperConnectionManager
"""

from abc import ABC, abstractmethod

from action_machine.core.meta_gate_hosts import ResourceMetaGateHost


class BaseResourceManager(ABC, ResourceMetaGateHost):
    """
    Базовый абстрактный класс для всех ресурсных менеджеров.

    Позволяет идентифицировать ресурс через isinstance. Наследует
    ResourceMetaGateHost, что делает декоратор @meta обязательным
    для всех конкретных реализаций.

    Каждый ресурсный менеджер обязан:
    1. Иметь декоратор @meta(description="...") с описанием.
    2. Реализовать метод get_wrapper_class(), возвращающий класс-обёртку
       для передачи ресурса в дочерние действия, или None если обёртка
       не требуется.
    """

    @abstractmethod
    def get_wrapper_class(self) -> type["BaseResourceManager"] | None:
        """
        Возвращает класс-обёртку (прокси) для данного ресурса.

        Обёртка создаётся автоматически при передаче connections в дочерние
        действия через ToolsBox.run(). Это гарантирует, что дочернее действие
        не может управлять транзакциями, но может выполнять запросы.

        Если обёртка не требуется (ресурс безопасен для прямой передачи),
        возвращает None — тогда ресурс передаётся как есть.

        Возвращает:
            Класс-обёртку (подкласс BaseResourceManager) или None.
        """
        pass
