# src/action_machine/core/components/aspect_executor.py
"""
Aspect executor component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated component for aspect execution in machine orchestration.
This Step 5 implementation owns regular/summary execution paths, including
`context_requires`, checker validation, and state merge.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        ├── AspectExecutor.execute_regular(...)
                │
        │       ├── call(...)
        │       ├── checker application
        │       ├── state merge
        │       └── optional saga frame append
        │
        └── AspectExecutor.execute_summary(...)
                └── call(...)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- `call(...)` owns ContextView injection and per-aspect `ScopedLogger` wiring.
- Regular aspect execution validates checker contracts before state merge.
- State merge remains immutable (`BaseState` new instance per step).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `execute_regular(...)` returns merged `BaseState` and aspect payload dict.

Edge case:
- Regular aspect returning unknown fields raises `ValidationFieldError`.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Summary execution remains thin and delegates invocation to `call(...)`.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Aspect execution component.
CONTRACT: execute_regular/execute_summary orchestrate aspect invocation contracts.
INVARIANTS: checker validation and immutable state merge for regular aspects.
FLOW: call aspect -> validate result -> merge state -> optional saga frame.
FAILURES: TypeError/ValidationFieldError for invalid regular aspect payload.
EXTENSION POINTS: custom execution policy can replace this component.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import time
from typing import Any, Protocol, cast

from action_machine.aspects.aspect_gate_host_inspector import AspectGateHostInspector
from action_machine.checkers.checker_gate_host_inspector import CheckerGateHostInspector
from action_machine.context.context_view import ContextView
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import ValidationFieldError
from action_machine.core.saga_frame import SagaFrame
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.resource_managers.base_resource_manager import BaseResourceManager


class AspectExecutor:
    """Component owning regular/summary aspect execution behavior."""

    @staticmethod
    def _apply_checkers(
        checkers: tuple[CheckerGateHostInspector.Snapshot.Checker, ...],
        result: dict[str, Any],
    ) -> None:
        """Run checker instances against a regular-aspect state patch."""
        for checker_meta in checkers:
            checker_instance = checker_meta.checker_class(
                checker_meta.field_name,
                required=checker_meta.required,
                **checker_meta.extra_params,
            )
            checker_instance.check(result)

    async def call(
        self,
        machine: _MachineLike,
        *,
        aspect_meta: AspectGateHostInspector.Snapshot.Aspect | None,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Any,
    ) -> Any:
        """Call one aspect preserving ContextView and per-aspect logging."""
        if aspect_meta is None:
            return BaseResult()

        aspect_log = ScopedLogger(
            coordinator=machine._log_coordinator,
            nest_level=box.nested_level,
            machine_name=machine.__class__.__name__,
            mode=machine._mode,
            action_name=action.get_full_class_name(),
            aspect_name=aspect_meta.method_name,
            context=context,
            state=state,
            params=params,
        )
        aspect_box = ToolsBox(
            run_child=box.run_child,
            factory=box.factory,
            resources=box.resources,
            context=context,
            log=aspect_log,
            nested_level=box.nested_level,
            rollup=box.rollup,
        )
        if aspect_meta.context_keys:
            ctx_view = ContextView(context, aspect_meta.context_keys)
            method_ref = cast(Any, aspect_meta.method_ref)
            return await method_ref(
                action, params, state, aspect_box, connections, ctx_view,
            )
        method_ref = cast(Any, aspect_meta.method_ref)
        return await method_ref(
            action, params, state, aspect_box, connections,
        )

    async def execute_regular(
        self,
        machine: _MachineLike,
        *,
        aspect_meta: AspectGateHostInspector.Snapshot.Aspect,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Any,
        runtime: _RuntimeLike,
        saga_stack: list[SagaFrame],
    ) -> tuple[BaseState, dict[str, Any], float]:
        """Execute one regular aspect with checker validation and state merge."""
        state_before = state
        aspect_start = time.time()
        new_state_dict = await self.call(
            machine,
            aspect_meta=aspect_meta,
            action=action,
            params=params,
            state=state,
            box=box,
            connections=connections,
            context=context,
        )
        if not isinstance(new_state_dict, dict):
            raise TypeError(
                f"Aspect {aspect_meta.method_name} must return a dict, "
                f"got {type(new_state_dict).__name__}"
            )

        checkers = runtime.checkers_by_aspect.get(aspect_meta.method_name, ())
        if not checkers and new_state_dict:
            raise ValidationFieldError(
                f"Aspect {aspect_meta.method_name} has no checkers, "
                f"but returned non-empty state: {new_state_dict}. "
                f"Either add checkers for all fields, or return an empty dict."
            )
        if checkers:
            allowed_fields = {c.field_name for c in checkers}
            extra_fields = set(new_state_dict.keys()) - allowed_fields
            if extra_fields:
                raise ValidationFieldError(
                    f"Aspect {aspect_meta.method_name} returned extra fields: "
                    f"{extra_fields}. Allowed only: {allowed_fields}"
                )
            self._apply_checkers(checkers, new_state_dict)

        merged_state = BaseState(**{**state.to_dict(), **new_state_dict})
        if runtime.has_compensators:
            compensator = runtime.compensators_by_aspect.get(aspect_meta.method_name)
            saga_stack.append(
                SagaFrame(
                    compensator=compensator,
                    aspect_name=aspect_meta.method_name,
                    state_before=state_before,
                    state_after=merged_state,
                )
            )

        duration_s = time.time() - aspect_start
        return merged_state, new_state_dict, duration_s

    async def execute_summary(
        self,
        machine: _MachineLike,
        *,
        summary_meta: AspectGateHostInspector.Snapshot.Aspect | None,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Any,
    ) -> tuple[object, float]:
        """Execute summary aspect and return result with duration."""
        if summary_meta is None:
            return BaseResult(), 0.0
        summary_start = time.time()
        result = await self.call(
            machine,
            aspect_meta=summary_meta,
            action=action,
            params=params,
            state=state,
            box=box,
            connections=connections,
            context=context,
        )
        return result, (time.time() - summary_start)


class _MachineLike(Protocol):
    _log_coordinator: Any
    _mode: str


class _RuntimeLike(Protocol):
    @property
    def checkers_by_aspect(
        self,
    ) -> dict[str, tuple[CheckerGateHostInspector.Snapshot.Checker, ...]]: ...

    @property
    def has_compensators(self) -> bool: ...

    @property
    def compensators_by_aspect(self) -> dict[str, Any]: ...
