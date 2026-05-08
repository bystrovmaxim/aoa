# packages/aoa-action-machine/src/aoa/action_machine/runtime/__init__.py
"""
Runtime package public entry points.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exposes runtime machine APIs, binding helpers, and execution
components used to run ActionMachine actions in production using
``NodeGraphCoordinator`` metadata inside ``ActionProductMachine`` and adapters.

Import concrete types from their modules (for example
``from aoa.action_machine.runtime.action_product_machine import ActionProductMachine``)
rather than from this ``__init__`` so the package root stays free of eager imports
that would create cycles with context / model / intents.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Runtime package import
           |
           +--> submodules (components, coordinators, ...)
                         |
                         v
                runtime machine execution pipeline

"""

from __future__ import annotations

__all__: list[str] = []
