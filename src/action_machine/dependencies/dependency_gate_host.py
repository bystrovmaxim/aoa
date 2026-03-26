# src/action_machine/dependencies/dependency_gate_host.py
"""
Модуль: DependencyGateHost — маркерный миксин для декоратора @depends.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

DependencyGateHost[T] — generic-миксин, который выполняет ДВЕ функции:

1. МАРКЕР: декоратор @depends при применении проверяет, что целевой класс
   наследует DependencyGateHost. Если нет — TypeError. Это гарантирует,
   что @depends нельзя повесить на произвольный класс.

2. ОГРАНИЧИТЕЛЬ ТИПА (bound): параметр T определяет, какие классы
   допускаются в качестве зависимостей. Например:
   - DependencyGateHost[object]              → любой класс
   - DependencyGateHost[BaseResourceManager] → только ресурс-менеджеры

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        RoleGateHost,
        DependencyGateHost[object],     ← bound = object (любой класс)
        CheckerGateHost,
        AspectGateHost,
        ConnectionGateHost,
    ): ...

    @depends(PaymentService, description="...")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    # Декоратор @depends проверяет:
    #   1. issubclass(cls, DependencyGateHost) → OK
    #   2. issubclass(PaymentService, cls._depends_bound) → OK (bound=object)
    #   3. Дубликатов нет → OK
    #   4. Добавляет DependencyInfo в cls._depends_info

    # MetadataBuilder.build(CreateOrderAction) читает:
    #   cls._depends_info   → [DependencyInfo(PaymentService, "...")]
    #   cls._depends_bound  → object

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Разрешить любые зависимости:
    class MyAction(DependencyGateHost[object]):
        pass

    # Ограничить зависимости только ресурс-менеджерами:
    class ResourcePool(DependencyGateHost[BaseResourceManager]):
        pass

    @depends(PostgresManager)   # OK — PostgresManager < BaseResourceManager
    @depends(PaymentService)    # TypeError — PaymentService не < BaseResourceManager
    class MyPool(ResourcePool):
        ...
"""

from __future__ import annotations

from typing import Any, ClassVar, get_args, get_origin


class DependencyGateHost[T]:
    """
    Маркерный generic-миксин, разрешающий использование декоратора @depends.

    Класс, НЕ наследующий DependencyGateHost, не может быть целью @depends —
    декоратор выбросит TypeError при попытке применения.

    Generic-параметр T определяет bound — базовый тип, которому должны
    соответствовать все зависимости, объявленные через @depends.
    Декоратор проверяет issubclass(klass, bound) при каждом вызове.

    Атрибуты уровня класса (создаются динамически):
        _depends_info : list[DependencyInfo]
            Временный список, заполняемый декоратором @depends.
            Читается MetadataBuilder при сборке ClassMetadata.

        _depends_bound : type
            Тип-ограничитель, извлечённый из generic-параметра T.
            Устанавливается в __init_subclass__. По умолчанию object.
    """

    # Аннотации для mypy, чтобы линтер знал о существовании динамических атрибутов
    _depends_info: ClassVar[list[Any]]
    _depends_bound: ClassVar[type]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается Python при создании подкласса DependencyGateHost.

        Извлекает bound-тип из generic-параметра и сохраняет
        в cls._depends_bound.
        """
        super().__init_subclass__(**kwargs)
        cls._depends_bound = _extract_bound(cls)

    @classmethod
    def get_depends_bound(cls) -> type:
        """
        Возвращает тип-ограничитель (bound) для зависимостей этого класса.

        Возвращает:
            type — bound-тип. По умолчанию object.
        """
        return getattr(cls, "_depends_bound", object)


def _extract_bound(cls: type) -> type:
    """
    Извлекает тип-ограничитель T из DependencyGateHost[T] в базовых классах.

    Обходит cls.__orig_bases__ и ищет запись вида DependencyGateHost[X].
    Если X — конкретный тип (не TypeVar) — возвращает его.
    Если X — TypeVar или не найден — пытается унаследовать от родителя.
    Если ничего не нашлось — возвращает object.

    Аргументы:
        cls: класс, для которого извлекается bound.

    Возвращает:
        type — bound-тип. По умолчанию object.
    """
    for base in getattr(cls, "__orig_bases__", ()):
        origin = get_origin(base)
        if origin is DependencyGateHost:
            args = get_args(base)
            if args and isinstance(args[0], type):
                return args[0]

    for parent in cls.__mro__[1:]:
        bound = getattr(parent, "_depends_bound", None)
        if bound is not None:
            return bound  # type: ignore[no-any-return]


    return object
