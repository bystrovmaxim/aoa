# src/action_machine/dependencies/__init__.py
"""
Пакет управления зависимостями ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит систему объявления, валидации и резолва зависимостей действий.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- DependencyIntent[T] — маркерный generic-миксин, разрешающий @depends.
  Параметр T задаёт bound — какие классы допустимы как зависимости.
  Например: DependencyIntent[object] — любой класс,
  DependencyIntent[BaseResourceManager] — только ресурс-менеджеры.
  Наследуется BaseAction.

- DependencyInfo — frozen-датакласс, описывающий одну зависимость:
  класс, опциональная фабрика, описание. Создаётся декоратором @depends.

- depends — декоратор уровня класса для объявления зависимостей.
  Проверяет issubclass(cls, DependencyIntent), проверяет bound,
  записывает DependencyInfo в cls._depends_info.

- DependencyFactory — stateless-фабрика, резолвящая зависимости.
  Принимает tuple[DependencyInfo, ...] (из снимка ``depends`` координатора).
  Каждый вызов resolve() создаёт новый экземпляр (кеш экземпляров отсутствует).
  Синглтоны реализуются через lambda-замыкание в @depends(factory=...).

- ``cached_dependency_factory`` / ``clear_dependency_factory_cache`` —
  кеш ``DependencyFactory`` на экземпляре ``GateCoordinator`` (словарь в ``__dict__``).

═══════════════════════════════════════════════════════════════════════════════
ТИПИЧНЫЙ ПОТОК
═══════════════════════════════════════════════════════════════════════════════

    1. @depends(PaymentService) записывает DependencyInfo в cls._depends_info.
    2. Инспектор ``depends`` строит снимок из ``_depends_info``.
    3. ``cached_dependency_factory(coordinator, cls)`` читает
       ``coordinator.get_snapshot(cls, \"depends\")`` и строит DependencyFactory.
    4. ToolsBox.resolve(PaymentService) делегирует в фабрику.
"""

from .dependency_factory import (
    DependencyFactory,
    DependencyInfo,
    cached_dependency_factory,
    clear_dependency_factory_cache,
)
from .dependency_intent import DependencyIntent
from .depends_decorator import depends

__all__ = [
    "DependencyFactory",
    "DependencyInfo",
    "DependencyIntent",
    "cached_dependency_factory",
    "clear_dependency_factory_cache",
    "depends",
]
