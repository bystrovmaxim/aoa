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

- DependencyGateHost[T] — маркерный generic-миксин, разрешающий @depends.
  Параметр T задаёт bound — какие классы допустимы как зависимости.
  Например: DependencyGateHost[object] — любой класс,
  DependencyGateHost[BaseResourceManager] — только ресурс-менеджеры.
  Наследуется BaseAction.

- DependencyInfo — frozen-датакласс, описывающий одну зависимость:
  класс, опциональная фабрика, описание. Создаётся декоратором @depends.

- depends — декоратор уровня класса для объявления зависимостей.
  Проверяет issubclass(cls, DependencyGateHost), проверяет bound,
  записывает DependencyInfo в cls._depends_info.

- DependencyFactory — stateless-фабрика, резолвящая зависимости.
  Принимает tuple[DependencyInfo, ...] из ClassMetadata.dependencies.
  Каждый вызов resolve() создаёт новый экземпляр (кеш отсутствует).
  Синглтоны реализуются через lambda-замыкание в @depends(factory=...).

═══════════════════════════════════════════════════════════════════════════════
ТИПИЧНЫЙ ПОТОК
═══════════════════════════════════════════════════════════════════════════════

    1. @depends(PaymentService) записывает DependencyInfo в cls._depends_info.
    2. MetadataBuilder.build(cls) читает _depends_info → ClassMetadata.dependencies.
    3. GateCoordinator.get_factory(cls) передаёт metadata.dependencies
       напрямую в DependencyFactory (без промежуточного шлюза).
    4. ToolsBox.resolve(PaymentService) делегирует в фабрику.
"""

from .dependency_factory import DependencyFactory, DependencyInfo
from .dependency_gate_host import DependencyGateHost
from .depends import depends

__all__ = [
    "DependencyFactory",
    "DependencyGateHost",
    "DependencyInfo",
    "depends",
]
