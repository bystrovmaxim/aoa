# src/action_machine/resources/base_resource_manager.py
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
Обёртка запрещает управление жизненным циклом ресурса (open/begin/commit/rollback),
но разрешает выполнение запросов (execute).

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНЫЙ ДЕКОРАТОР @meta
═══════════════════════════════════════════════════════════════════════════════

Каждый ресурсный менеджер обязан иметь декоратор @meta с описанием.
Контролируется ResourceMetaIntent, который входит в цепочку наследования
BaseResourceManager. MetadataBuilder при сборке проверяет: если класс
наследует ResourceMetaIntent — @meta обязателен. Без него — TypeError.

═══════════════════════════════════════════════════════════════════════════════
ПОДДЕРЖКА ROLLUP
═══════════════════════════════════════════════════════════════════════════════

Режим rollup позволяет безопасно тестировать на production-базе: все
операции записи выполняются внутри транзакции, но вместо COMMIT
выполняется ROLLBACK. Это обеспечивает полноценное выполнение
бизнес-логики без побочных эффектов в базе данных.

Метод check_rollup_support() определяет, поддерживает ли конкретный
менеджер режим rollup. По умолчанию выбрасывает RollupNotSupportedError —
менеджеры, поддерживающие rollup (например, SqlConnectionManager),
переопределяют этот метод.

DependencyFactory.resolve() при rollup=True вызывает check_rollup_support()
для каждого экземпляра BaseResourceManager. Если менеджер не поддерживает
rollup — RollupNotSupportedError пробрасывается наружу, и тестировщик
узнаёт об этом немедленно.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseResourceManager(ABC, ResourceMetaIntent):
        check_rollup_support() → raises RollupNotSupportedError
        get_wrapper_class()    → type | None

    class SqlConnectionManager(BaseResourceManager):
        check_rollup_support() → True  (переопределяет, поддерживает rollup)
        __init__(rollup=False)         (принимает флаг rollup)
        commit()                       (при rollup=True → rollback вместо commit)

    @meta(description="Менеджер PostgreSQL", domain=WarehouseDomain)
    class PostgresConnectionManager(SqlConnectionManager):
        __init__(params, rollup=False) (прокидывает rollup в super)

    @meta(description="Менеджер Redis-кеша", domain=CacheDomain)
    class RedisManager(BaseResourceManager):
        check_rollup_support()         (НЕ переопределяет → RollupNotSupportedError)

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Production — rollup выключен:
    db = PostgresConnectionManager(params)
    await db.open()
    await db.begin()
    await db.execute("INSERT ...")
    await db.commit()  # → реальный COMMIT

    # Тестирование на production-базе — rollup включён:
    db = PostgresConnectionManager(params, rollup=True)
    await db.open()
    await db.begin()
    await db.execute("INSERT ...")
    await db.commit()  # → ROLLBACK вместо COMMIT

    # Менеджер без поддержки rollup:
    redis = RedisManager(config)
    redis.check_rollup_support()  # → RollupNotSupportedError
"""

from abc import ABC, abstractmethod

from action_machine.intents.meta.meta_intents import ResourceMetaIntent
from action_machine.model.exceptions import RollupNotSupportedError


class BaseResourceManager(ABC, ResourceMetaIntent):
    """
    Базовый абстрактный класс для всех ресурсных менеджеров.

    Позволяет идентифицировать ресурс через isinstance. Наследует
    ResourceMetaIntent, что делает декоратор @meta обязательным
    для всех конкретных реализаций.

    Каждый ресурсный менеджер обязан:
    1. Иметь декоратор @meta(description="...", domain=SomeDomain) с описанием и доменом.
    2. Реализовать метод get_wrapper_class(), возвращающий класс-обёртку
       для передачи ресурса в дочерние действия, или None если обёртка
       не требуется.

    Менеджеры, поддерживающие транзакционный откат (rollup), должны
    переопределить check_rollup_support() и вернуть True. По умолчанию
    метод выбрасывает RollupNotSupportedError.
    """

    def check_rollup_support(self) -> bool:
        """
        Проверяет, поддерживает ли менеджер режим rollup (автооткат транзакций).

        Режим rollup используется для безопасного тестирования на production-базе:
        все операции записи выполняются, но при commit() происходит rollback()
        вместо реальной фиксации. Это позволяет проверить полный конвейер
        бизнес-логики без побочных эффектов.

        Поведение по умолчанию: выбрасывает RollupNotSupportedError.
        Менеджеры с транзакционной поддержкой (SqlConnectionManager и его
        наследники) переопределяют этот метод и возвращают True.

        Возвращает:
            True если менеджер поддерживает rollup.

        Исключения:
            RollupNotSupportedError: если менеджер не поддерживает rollup.
                Сообщение содержит имя класса для диагностики.
        """
        raise RollupNotSupportedError(
            f"Класс '{type(self).__name__}' не поддерживает rollup. "
            f"Реализуйте метод check_rollup_support() или используйте "
            f"ресурс, поддерживающий транзакционный откат."
        )

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
