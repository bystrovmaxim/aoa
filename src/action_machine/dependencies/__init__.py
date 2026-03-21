# src/action_machine/dependencies/__init__.py
"""
Пакет управления зависимостями в ActionMachine.

Содержит:
- DependencyGate: шлюз для хранения информации о зависимостях, объявленных через @depends.
- DependencyGateHost: миксин, который присоединяет DependencyGate к классу действия.
- DependencyFactory: фабрика для создания экземпляров зависимостей.
- depends: декоратор для объявления зависимостей действия.

Этот пакет выделен из Core для улучшения модульности.
"""

from .dependency_factory import DependencyFactory
from .dependency_gate import DependencyGate, DependencyInfo
from .dependency_gate_host import DependencyGateHost
from .depends import depends

__all__ = [
    "DependencyGate",
    "DependencyInfo",
    "DependencyGateHost",
    "DependencyFactory",
    "depends",
]