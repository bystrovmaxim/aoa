# src/action_machine/core/components/__init__.py
"""
Core execution components for ActionProductMachine decomposition.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose dedicated execution components used to split orchestration concerns in
`ActionProductMachine` into isolated responsibilities.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Target orchestration flow (final state after migration):

::

    ┌──────────────────────────────────────────────────────────────────────────────┐
    │                     ActionProductMachine (Thin Orchestrator)                 │
    │                                                                              │
    │ run(context, action, params, connections)                                    │
    │   1) role_checker.check(action_cls, user_roles)                              │
    │   2) connections = connection_validator.validate(action_cls, connections)    │
    │   3) box = tools_box_factory.create(nest_level, context, action_cls,         │
    │                                     params, resources, rollup, run_child)    │
    │   4) rollback/error flow uses saga_coordinator.rollback(...)                 │
    │   5) return result                                                           │
    └──────────────────────────────────────────────────────────────────────────────┘
                                         │ delegates
                                         ▼
    ┌─────────────────────────── Core Components ──────────────────────────────────┐
    │ RoleChecker            -> GateCoordinator role snapshot / AuthorizationError │
    │ ConnectionValidator    -> GateCoordinator connection snapshot / validation   │
    │ ToolsBoxFactory        -> ToolsBox with depth, rollup, nested-run callback   │
    │ AspectExecutor         -> aspect invoke + context injection + checkers/state │
    │ ErrorHandlerExecutor   -> @on_error resolution + fallback semantics          │
    │ SagaCoordinator        -> regular/summary flow + rollback + plugin/log events│
    └──────────────────────────────────────────────────────────────────────────────┘

During migration (current scaffolding phase), components delegate to existing
machine internals. The final state above will be reached incrementally.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- One entity per file (class or dataclass).
- No shared "god-modules" with mixed unrelated responsibilities.
- Components are initialized in deterministic dependency order.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path (current Step 1):
- Components are wired in constructor and delegate to existing machine methods.

Edge case:
- Calling placeholder `ToolsBoxFactory.create()` before Step 4 raises
  `NotImplementedError` by design.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This package introduces component boundaries and extension points. Runtime
execution logic remains in `ActionProductMachine` until later migration steps.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Core components package API surface.
CONTRACT: Export isolated execution components.
INVARIANTS: one file per entity; deterministic composition order.
FLOW: machine constructor wires components -> run delegates in later steps.
FAILURES: no behavior changes expected at this scaffold stage.
EXTENSION POINTS: components are constructor-injectable for tests/customization.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from .aspect_executor import AspectExecutor
from .connection_validator import ConnectionValidator
from .error_handler_executor import ErrorHandlerExecutor
from .role_checker import RoleChecker
from .saga_coordinator import SagaCoordinator
from .tools_box_factory import ToolsBoxFactory

__all__ = [
    "AspectExecutor",
    "ConnectionValidator",
    "ErrorHandlerExecutor",
    "RoleChecker",
    "SagaCoordinator",
    "ToolsBoxFactory",
]
