# src/action_machine/core/coordinator_action_product_machine.py
"""
CoordinatorActionProductMachine — вариант машины, читающий конвейер из facet-снимков.

Наследует ``ActionProductMachine`` и переопределяет только построение
``_ActionExecutionCache`` и ``DependencyFactory``: вместо ``BaseAction.scratch_*``
и ``cls._depends_info`` используются ``GateCoordinator.get_snapshot(...)``.

Предназначен для сравнения производительности со scratch-first путём (см. тесты
в ``tests/bench/``).
"""

from __future__ import annotations

from action_machine.core.action_product_machine import (
    ActionProductMachine,
    _ActionExecutionCache,
)
from action_machine.dependencies.dependency_factory import DependencyFactory


class CoordinatorActionProductMachine(ActionProductMachine):
    """
    Асинхронная машина действий с чтением метаданных конвейера из координатора.

    Роли по-прежнему из снимка ``role`` (как у базовой машины). Остальные
    фрагменты конвейера — из снимков ``aspect``, ``checker``, ``compensator``,
    ``error_handler``, ``connections``; зависимости — из снимка ``depends``.
    """

    def _get_execution_cache(self, action_cls: type) -> _ActionExecutionCache:
        return _ActionExecutionCache.from_coordinator_facets(
            action_cls,
            gate_coordinator=self._coordinator,
        )

    def _dependency_factory_for(self, action_cls: type) -> DependencyFactory:
        snap = self._coordinator.get_snapshot(action_cls, "depends")
        if snap is None or not hasattr(snap, "dependencies"):
            return DependencyFactory(())
        return DependencyFactory(tuple(snap.dependencies))
