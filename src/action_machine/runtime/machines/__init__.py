# src/action_machine/runtime/machines/__init__.py
"""
Re-exports for runtime machines (canonical modules live on ``action_machine.runtime``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Backward-compatible import path: ``action_machine.runtime.machines.*`` maps to
the flat ``action_machine.runtime`` machine modules. ``Core`` lives in
``action_machine.legacy.core``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Compatibility shim for former ``runtime.machines`` package layout.
CONTRACT: Re-export async/sync machines; ``Core`` is ``action_machine.legacy.core``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from action_machine.runtime.action_product_machine import ActionProductMachine
from action_machine.runtime.sync_action_product_machine import SyncActionProductMachine

__all__ = [
    "ActionProductMachine",
    "SyncActionProductMachine",
]
