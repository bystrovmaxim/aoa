"""Core package public exports.

Canonical coordinator assembly lives in ``CoreActionMachine``:
it creates ``GateCoordinator``, registers all default inspectors, and builds it.
Production machines consume a built coordinator (fail-fast contract).


AI-CORE-BEGIN
ROLE: module __init__
CONTRACT: Keep runtime behavior unchanged; documentation defines key contracts and flow for humans and AI.
INVARIANTS: Preserve declared interfaces and validation semantics.
FLOW: declaration -> inspector/coordinator snapshot -> runtime consumption.
AI-CORE-END
"""

from action_machine.core.coordinator_action_product_machine import (
    CoordinatorActionProductMachine,
)
from action_machine.core.core_action_machine import CoreActionMachine

__all__ = ["CoordinatorActionProductMachine", "CoreActionMachine"]
