# src/action_machine/runtime/__init__.py
"""
Runtime package public entry points.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exposes runtime machine APIs, binding helpers, and execution
components used to run ActionMachine actions in production.

Canonical coordinator assembly lives in ``Core``: it creates a
``GraphCoordinator``, registers default inspectors, and builds the graph/facets.
Production machines consume a built coordinator as a fail-fast contract.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Runtime package import
           |
           +--> lightweight modules (navigation, components)
           |
           +--> lazy Core access via __getattr__ (Core lives in ``action_machine.legacy.core``)
                         |
                         v
                create/build GraphCoordinator
                         |
                         v
                runtime machine execution pipeline

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.legacy.core import Core

__all__ = ["Core"]


def __getattr__(name: str) -> object:
    if name == "Core":
        from action_machine.legacy.core import Core  # pylint: disable=import-outside-toplevel

        return Core
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
