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

- ContextView injection behavior is delegated through `call(...)` and preserved.
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

from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import ValidationFieldError
from action_machine.core.saga_frame import SagaFrame


class AspectExecutor:
    """Component owning regular/summary aspect execution behavior."""

    async def call(
        self,
        machine: object,
        *,
        aspect_meta,
        action,
        params,
        state,
        box,
        connections,
        context,
    ):
        """Call one aspect preserving context injection semantics."""
        return await machine._call_aspect(  # noqa: SLF001
            aspect_meta=aspect_meta,
            action=action,
            params=params,
            state=state,
            box=box,
            connections=connections,
            context=context,
        )

    async def execute_regular(
        self,
        machine: object,
        *,
        aspect_meta,
        action,
        params,
        state: BaseState,
        box,
        connections,
        context,
        runtime,
        saga_stack: list[SagaFrame],
    ) -> tuple[BaseState, dict, float]:
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
            machine._apply_checkers(checkers, new_state_dict)  # noqa: SLF001

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
        machine: object,
        *,
        summary_meta,
        action,
        params,
        state: BaseState,
        box,
        connections,
        context,
    ) -> tuple[object, float]:
        """Execute summary aspect and return result with duration."""
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