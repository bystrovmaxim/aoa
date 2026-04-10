# src/action_machine/core/components/aspect_executor.py
"""
Aspect executor component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a component entry point for the aspect invocation stage in the machine
orchestration. Currently delegates to existing machine internals; full logic
migration happens in a later step.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine / SagaCoordinator
        │
        └── AspectExecutor.call(machine, aspect_meta, action, params,
                                state, box, connections, context)
                │
                └── machine._call_aspect(...)   // temporary delegation

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Delegation target remains stable during scaffolding phase.
- Return value contract (dict for regular, BaseResult for summary) is preserved.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `call(...)` returns regular-aspect state patch dictionary.

Edge case:
- For summary aspect, delegated call returns final `BaseResult`.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Implementation is temporary and delegates to a private machine method.
- All exceptions from the underlying method propagate unchanged.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Aspect executor scaffolding.
CONTRACT: call(...) -> aspect result (dict or BaseResult).
INVARIANTS: delegation is temporary; signature matches protocol.
FLOW: machine -> AspectExecutor.call -> legacy machine method.
FAILURES: propagates ValidationFieldError, TypeError, etc.
EXTENSION POINTS: future replacement with direct aspect execution logic.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations


class AspectExecutor:
    """Component entry point for aspect invocation stage.

    This is a scaffolding implementation that delegates to the existing
    machine's internal method. Full migration of aspect execution logic will
    happen in a subsequent step.
    """

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
        """Delegate aspect call to current machine logic."""
        return await machine._call_aspect(  # noqa: SLF001
            aspect_meta=aspect_meta,
            action=action,
            params=params,
            state=state,
            box=box,
            connections=connections,
            context=context,
        )