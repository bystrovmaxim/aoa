# src/action_machine/runtime/tools_box_factory.py
"""
ToolsBox factory component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated entry point for toolbox construction in machine execution.
This Step 4 implementation creates ``ToolsBox`` instances with preserved
nested-level and rollup semantics. It uses an explicit ``DependencyFactoryResolver``
and logging metadata (``mode``, ``machine_class_name``) instead of reading
private fields from the machine.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine._run_internal
        │
        └── ToolsBoxFactory.create(
                factory_resolver=self,
                nest_level, context, action_cls, params,
                resources, rollup, run_child,
                mode=self._mode,
                machine_class_name=self.__class__.__name__,
            )
                │
                ├── ScopedLogger(..., domain=resolve_domain(action_cls))
                ├── factory = factory_resolver.dependency_factory_for(action_cls)
                └── returns ToolsBox

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    ``create(...)`` returns a fully configured ``ToolsBox`` for one execution
    scope with logger, dependencies, and resources wired.

Edge case:
    Nested ``run_child`` callback receives the same ``rollup`` value as parent
    run scope, preserving rollback semantics.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: ToolsBox factory component.
CONTRACT: create(...) -> configured ToolsBox.
INVARIANTS: explicit resolver + mode strings; no private machine access.
FLOW: resolver + runtime args -> logger/factory wiring -> ToolsBox.
FAILURES: propagates dependency resolution errors.
EXTENSION POINTS: custom toolbox construction strategy via component injection.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.logging.domain_resolver import resolve_domain
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.model.base_state import BaseState
from action_machine.runtime.dependency_factory_resolver import (
    DependencyFactoryResolver,
)
from action_machine.runtime.tools_box import ToolsBox


class ToolsBoxFactory:
    """Component entry point for toolbox creation stage.

    Step 4 implementation of toolbox construction with nested-run propagation.
    """

    def __init__(self, log_coordinator: LogCoordinator) -> None:
        self._log_coordinator = log_coordinator

    def create(
        self,
        *,
        factory_resolver: DependencyFactoryResolver,
        nest_level: int,
        context: Any,
        action_cls: type,
        params: Any,
        resources: Any,
        rollup: bool,
        run_child: Any,
        mode: str,
        machine_class_name: str,
    ) -> ToolsBox:
        """Create a configured ToolsBox for one execution scope."""
        action_name = f"{action_cls.__module__}.{action_cls.__name__}"
        log = ScopedLogger(
            coordinator=self._log_coordinator,
            nest_level=nest_level,
            machine_name=machine_class_name,
            mode=mode,
            action_name=action_name,
            aspect_name="",
            context=context,
            state=BaseState(),
            params=params,
            domain=resolve_domain(action_cls),
        )
        factory = factory_resolver.dependency_factory_for(action_cls)
        return ToolsBox(
            run_child=run_child,
            factory=factory,
            resources=resources,
            log=log,
            nested_level=nest_level,
            rollup=rollup,
        )
