# src/action_machine/core/components/tools_box_factory_protocol.py
"""
Protocol for ToolsBox factory component.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the contract for constructing `ToolsBox` instances used during action
execution. The factory encapsulates creation of scoped logger, dependency
resolution context, and nested‑run callback wiring.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── ToolsBoxFactoryProtocol.create(...)
                │
                ├── builds ScopedLogger with current nest_level and context
                ├── resolves dependencies via DependencyFactory (cached on coordinator)
                ├── wraps `run_child` closure for nested action execution
                └── returns fully configured ToolsBox instance

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The returned `ToolsBox` must be immutable after creation.
- The `run_child` callback must preserve the original `rollup` flag and
  `resources` dictionary across nested invocations.
- Factory must not cache `ToolsBox` instances; each call creates a new instance.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- Factory returns a new `ToolsBox` for current nest level and context.

Edge case:
- Nested action run uses provided `run_child` callback and preserves rollup.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- The protocol does not specify how `DependencyFactory` is obtained; that is
  an implementation detail (typically via `GateCoordinator` snapshot).
- Errors during dependency resolution (e.g., missing `@depends`) propagate
  to the caller.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: ToolsBox factory contract.
CONTRACT: create(...) -> ToolsBox.
INVARIANTS: each call returns new immutable instance; preserves rollup/nested semantics.
FLOW: machine -> factory.create -> ToolsBox ready for aspect execution.
FAILURES: propagates dependency resolution errors (ValueError, RollupNotSupportedError).
EXTENSION POINTS: custom factory can alter logger, dependency resolution, or run_child.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Protocol


class ToolsBoxFactoryProtocol(Protocol):
    """Contract for creating `ToolsBox` instances per run."""

    def create(
        self,
        machine: object,
        *,
        nest_level: int,
        context: Any,
        action_cls: type,
        params: Any,
        resources: dict[type, Any] | None,
        rollup: bool,
        run_child: Any,
    ) -> Any:
        """
        Build a toolbox for one action execution.

        Args:
            machine: The executing machine (provides log coordinator and coordinator).
            nest_level: Current nesting depth (0 for top‑level action).
            context: Execution context (user, request, runtime).
            action_cls: The action class being executed.
            params: Input parameters for the action (frozen `BaseParams`).
            resources: Optional external resources (e.g., mocks in tests).
            rollup: Whether transaction rollup mode is active.
            run_child: Callback to execute nested actions.
        """
        pass
