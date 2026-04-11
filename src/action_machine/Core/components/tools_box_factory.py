# src/action_machine/core/components/tools_box_factory.py
"""
ToolsBox factory component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated entry point for toolbox construction in machine execution.
This Step 4 implementation creates `ToolsBox` instances with preserved
nested-level and rollup semantics.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── ToolsBoxFactory.create(machine, nest_level, context, action_cls,
                                   params, resources, rollup, run_child)
                │
                ├── builds scoped logger for current nest level
                ├── resolves dependency factory for target action class
                └── returns configured ToolsBox

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Component receives references to `LogCoordinator` and `GateCoordinator`.
- Public `create(...)` API is stable for `ActionProductMachine` wiring.
- Returned `ToolsBox` preserves incoming `nest_level`, `resources`, and `rollup`.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `create(...)` returns a fully configured `ToolsBox` for one run scope.

Edge case:
- Nested `run_child` callback receives same `rollup` value as parent run.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This component intentionally reads machine internals (`_log_coordinator`,
`_dependency_factory_for`) so dependency wiring stays on the machine.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: ToolsBox factory component.
CONTRACT: create(...) -> configured ToolsBox.
INVARIANTS: preserves nested level and rollup semantics.
FLOW: machine + runtime args -> logger/factory wiring -> ToolsBox.
FAILURES: propagates dependency resolution errors.
EXTENSION POINTS: custom toolbox construction strategy via component injection.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Protocol

from action_machine.core.base_state import BaseState
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.metadata.gate_coordinator import GateCoordinator


class ToolsBoxFactory:
    """Component entry point for toolbox creation stage.

    Step 4 implementation of toolbox construction with nested-run propagation.
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
        machine: _MachineLike,
        *,
        nest_level: int,
        context: Any,
        action_cls: type,
        params: Any,
        resources: Any,
        rollup: bool,
        run_child: Any,
    ) -> ToolsBox:
        """Create a configured ToolsBox for one execution scope."""
        _ = (self._log_coordinator, self._coordinator)
        action_name = f"{action_cls.__module__}.{action_cls.__name__}"
        log = ScopedLogger(
            coordinator=machine._log_coordinator,
            nest_level=nest_level,
            machine_name=machine.__class__.__name__,
            mode=machine._mode,
            action_name=action_name,
            aspect_name="",
            context=context,
            state=BaseState(),
            params=params,
        )
        factory = machine._dependency_factory_for(action_cls)
        return ToolsBox(
            run_child=run_child,
            factory=factory,
            resources=resources,
            log=log,
            nested_level=nest_level,
            rollup=rollup,
        )


class _MachineLike(Protocol):
    _log_coordinator: LogCoordinator
    _mode: str

    def _dependency_factory_for(self, action_cls: type) -> Any: ...
