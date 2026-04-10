# src/action_machine/core/gate_coordinator.py
"""
Реэкспорт :class:`GateCoordinator`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Каноническая реализация живёт в ``action_machine.metadata.gate_coordinator``:
там задокументированы явный ``build()``, фасетный граф и ``get_snapshot``.

Этот модуль сохраняет **стабильный путь импорта** для ядра и прикладного кода:

    from action_machine.metadata.gate_coordinator import GateCoordinator

Поведение идентично импорту из ``action_machine.metadata``.
"""

from action_machine.metadata.gate_coordinator import GateCoordinator

__all__ = ["GateCoordinator"]
