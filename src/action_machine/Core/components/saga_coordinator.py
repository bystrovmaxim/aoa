"""
Saga coordinator component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated entry point for saga rollback coordination in machine
execution. At Step 1 this component preserves behavior by delegating to current
machine rollback implementation.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── SagaCoordinator.rollback(machine, **kwargs)
                │
                └── machine._rollback_saga(**kwargs)  // temporary delegation

Injected dependencies are stored to establish explicit wiring contract:
`AspectExecutor`, `ErrorHandlerExecutor`, `PluginCoordinator`, `LogCoordinator`.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Current rollback order and event semantics remain unchanged.
- Delegation is temporary; dependencies define future standalone implementation.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `rollback(...)` delegates and completes compensation unwind without re-raising
  compensator failures.

Edge case:
- Empty saga stack results in no-op rollback completion.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This class is scaffolding for decomposition. It does not yet own rollback flow
or handler routing logic; those remain in machine internals at this step.

AI-CORE-BEGIN
ROLE: Saga rollback coordination scaffolding.
CONTRACT: rollback(machine, **kwargs) delegates to existing rollback behavior.
INVARIANTS: rollback/event semantics preserved; dependency wiring explicit.
FLOW: machine error path -> SagaCoordinator.rollback -> machine rollback.
FAILURES: same behavior/exceptions as machine `_rollback_saga`.
EXTENSION POINTS: future migration to standalone rollback orchestration.
AI-CORE-END
"""

from __future__ import annotations

from action_machine.core.components.aspect_executor import AspectExecutor
from action_machine.core.components.error_handler_executor import ErrorHandlerExecutor
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugins.plugin_coordinator import PluginCoordinator


class SagaCoordinator:
    """Component entry point for saga rollback coordination."""

    def __init__(
        self,
        aspect_executor: AspectExecutor,
        error_handler_executor: ErrorHandlerExecutor,
        plugin_coordinator: PluginCoordinator,
        log_coordinator: LogCoordinator,
    ) -> None:
        self._aspect_executor = aspect_executor
        self._error_handler_executor = error_handler_executor
        self._plugin_coordinator = plugin_coordinator
        self._log_coordinator = log_coordinator

    async def rollback(self, machine: object, **kwargs) -> None:
        """Delegate rollback to current machine logic."""
        _ = (
            self._aspect_executor,
            self._error_handler_executor,
            self._plugin_coordinator,
            self._log_coordinator,
        )
        await machine._rollback_saga(**kwargs)  # noqa: SLF001

