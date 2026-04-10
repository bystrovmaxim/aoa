# src/action_machine/core/components/tools_box_factory.py
"""
ToolsBox factory component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a component entry point for the toolbox-creation stage in the machine
orchestration. Currently a placeholder; full logic migration happens in a later
step.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── ToolsBoxFactory.create(machine, nest_level, context, action_cls,
                                   params, resources, rollup, run_child)
                │
                └── (not yet implemented)   // placeholder for Step 1

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Component receives references to `LogCoordinator` and `GateCoordinator`.
- Method signature matches `ToolsBoxFactoryProtocol`.
- Placeholder raises `NotImplementedError` to prevent accidental use.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path (future Step 4):
- `create(...)` returns a fully configured `ToolsBox` for one run scope.

Edge case (current Step 1):
- `create(...)` raises `NotImplementedError` to make incomplete wiring explicit.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- `create()` is not implemented yet; calling it will raise `NotImplementedError`.
- Actual toolbox construction remains in `ActionProductMachine` until Step 4.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: ToolsBox factory scaffolding.
CONTRACT: create(...) -> ToolsBox (not yet implemented).
INVARIANTS: signature matches protocol; raises NotImplementedError.
FLOW: machine -> ToolsBoxFactory.create -> (placeholder).
FAILURES: NotImplementedError if called before implementation.
EXTENSION POINTS: future replacement with full toolbox construction logic.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.metadata.gate_coordinator import GateCoordinator


class ToolsBoxFactory:
    """Component entry point for toolbox creation stage.

    This is a scaffolding implementation that currently raises
    `NotImplementedError`. Full migration of toolbox construction logic will
    happen in a subsequent step (Step 4).
    """

    def __init__(
        self,
        log_coordinator: LogCoordinator,
        coordinator: GateCoordinator,
    ) -> None:
        self._log_coordinator = log_coordinator
        self._coordinator = coordinator

    def create(
        self,
        machine: object,
        *,
        nest_level: int,
        context,
        action_cls: type,
        params,
        resources,
        rollup: bool,
        run_child,
    ):
        """Placeholder API surface for toolbox-creation stage."""
        _ = (
            machine,
            nest_level,
            context,
            action_cls,
            params,
            resources,
            rollup,
            run_child,
            self._log_coordinator,
            self._coordinator,
        )
        raise NotImplementedError(
            "ToolsBoxFactory.create() is introduced in Step 1 as a placeholder. "
            "Actual implementation will be migrated in Step 4."
        )