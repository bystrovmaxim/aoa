# src/action_machine/dependencies/__init__.py
"""
Пакет управления зависимостями ActionMachine.

Содержит:
- DependencyGateHost[T] — маркерный generic-миксин, разрешающий @depends.
- DependencyGate — реестр зависимостей с поддержкой заморозки.
  Используется в ActionProductMachine для создания DependencyFactory.
- DependencyInfo — frozen-датакласс, описывающий одну зависимость.
- depends — декоратор для объявления зависимостей на классе.
- DependencyFactory — фабрика, резолвящая зависимости через ToolsBox.

Типичный поток:
    1. @depends(PaymentService) записывает DependencyInfo в cls._depends_info.
    2. MetadataBuilder.build(cls) читает _depends_info → ClassMetadata.dependencies.
    3. ActionProductMachine._get_factory() создаёт DependencyGate из metadata,
       оборачивает в DependencyFactory.
    4. ToolsBox.resolve(PaymentService) делегирует в фабрику.
"""

from .dependency_factory import DependencyFactory
from .dependency_gate import DependencyGate, DependencyInfo
from .dependency_gate_host import DependencyGateHost
from .depends import depends

__all__ = [
    "DependencyGate",
    "DependencyGateHost",
    "DependencyInfo",
    "DependencyFactory",
    "depends",
]