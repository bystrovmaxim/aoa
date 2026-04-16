# src/maxitor/test_domain/build.py
"""Собрать ``GateCoordinator`` по всем декларациям test_domain (только для графа)."""

from __future__ import annotations

import importlib
from typing import Final

from action_machine.graph.gate_coordinator import GateCoordinator

_MODULES: Final[tuple[str, ...]] = (
    "maxitor.roles",
    "maxitor.test_domain.dependencies",
    "maxitor.test_domain.domain",
    "maxitor.test_domain.entities",
    "maxitor.test_domain.plugins",
    "maxitor.test_domain.resources",
    "maxitor.test_domain.actions",
)


def build_test_coordinator() -> GateCoordinator:
    for name in _MODULES:
        importlib.import_module(name)
    from action_machine.runtime.machines.core_action_machine import CoreActionMachine

    return CoreActionMachine.create_coordinator()
