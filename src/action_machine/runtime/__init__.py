# src/action_machine/runtime/__init__.py
"""Runtime package: machines, binding helpers, and execution components.

Canonical coordinator assembly lives in ``CoreActionMachine``:
it creates ``GateCoordinator``, registers all default inspectors, and builds it.
Production machines consume a built coordinator (fail-fast contract).
``ActionProductMachine`` reads the aspect pipeline, connections, roles, and
``depends`` list only from coordinator facet snapshots (no scratch-first path).

``CoreActionMachine`` is exported lazily (``__getattr__``) so submodules such as
``runtime.navigation`` can be imported without pulling in the graph stack while
``model`` (and thus ``BaseSchema``) is still initializing.


AI-CORE-BEGIN
ROLE: module __init__
CONTRACT: Keep runtime behavior unchanged; documentation defines key contracts and flow for humans and AI.
INVARIANTS: Preserve declared interfaces and validation semantics.
FLOW: declaration -> inspector/coordinator snapshot -> runtime consumption.
AI-CORE-END
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.runtime.machines.core_action_machine import CoreActionMachine

__all__ = ["CoreActionMachine"]


def __getattr__(name: str) -> object:
    if name == "CoreActionMachine":
        from action_machine.runtime.machines.core_action_machine import CoreActionMachine  # pylint: disable=import-outside-toplevel

        return CoreActionMachine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
