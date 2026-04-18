# src/action_machine/runtime/components/__init__.py
"""
Runtime execution components for ActionProductMachine decomposition.

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
    ┌─────────────────────────── Runtime components ─────────────────────────────────┐
    │ RoleChecker            -> GraphCoordinator role snapshot / AuthorizationError │
    │ ConnectionValidator    -> GraphCoordinator connection snapshot / validation   │
    │ ToolsBoxFactory        -> ToolsBox (explicit resolver + mode + class name)   │
    │ AspectExecutor         -> aspect invoke (injected log coordinator + mode)     │
    │ ErrorHandlerExecutor   -> @on_error resolution + fallback semantics          │
    │ SagaCoordinator        -> regular/summary flow + rollback + plugin/log events│
    └──────────────────────────────────────────────────────────────────────────────┘

During migration (current scaffolding phase), components can delegate to
existing machine internals. The final state above is reached incrementally.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- One entity per file (class or dataclass).
- No shared "god-modules" with mixed unrelated responsibilities.
- Components are initialized in deterministic dependency order.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Components are wired in the machine constructor and invoked from
    ``_run_internal`` in deterministic order.

Edge case:
    Custom ``AspectExecutor`` or ``ToolsBoxFactory`` replacements must preserve
    current constructor and method signatures from their component modules.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Orchestration order and core contracts live in ``ActionProductMachine``.
This package exports component building blocks only.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Runtime components package API surface.
CONTRACT: Export isolated execution components.
INVARIANTS: one file per entity; deterministic composition order.
FLOW: machine constructor wires components -> run delegates in later steps.
FAILURES: no behavior changes expected at this scaffold stage.
EXTENSION POINTS: components are constructor-injectable for tests/customization.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from action_machine.runtime.components.aspect_executor import AspectExecutor
from action_machine.runtime.components.connection_validator import ConnectionValidator
from action_machine.runtime.components.dependency_factory_resolver import DependencyFactoryResolver
from action_machine.runtime.components.error_handler_executor import ErrorHandlerExecutor
from action_machine.runtime.components.role_checker import RoleChecker
from action_machine.runtime.components.saga_coordinator import SagaCoordinator
from action_machine.runtime.components.tools_box_factory import ToolsBoxFactory

__all__ = [
    "AspectExecutor",
    "ConnectionValidator",
    "DependencyFactoryResolver",
    "ErrorHandlerExecutor",
    "RoleChecker",
    "SagaCoordinator",
    "ToolsBoxFactory",
]
