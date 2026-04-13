# src/action_machine/intents/aspects/__init__.py
"""
Aspect pipeline declarations for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose decorators and marker mixin used to define action pipeline steps:
- ``regular_aspect`` for intermediate state-producing steps.
- ``summary_aspect`` for the final Result-producing step.
- ``AspectIntent`` as the intent marker for aspect-enabled classes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Decorators write method-level metadata (``_new_aspect_meta``). The inspector
collects that metadata into aspect snapshots during coordinator build. Runtime
execution then consumes those snapshots to run regular steps first and summary
step last.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- At most one summary aspect per class.
- If regular aspects exist, a summary aspect is required.
- Summary aspect must be declared last.
- Method naming suffixes are mandatory (``_aspect`` / ``_summary``).
- Description is required for both decorators.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.aspects import regular_aspect, summary_aspect

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        @regular_aspect("Validate data")
        async def validate_aspect(self, params, state, box, connections):
            return {"validated_user": params.user_id}

        @summary_aspect("Build result")
        async def build_result_summary(self, params, state, box, connections):
            return OrderResult(...)

Edge case: regular aspects without a summary aspect fail during metadata
validation.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This module only exports declarations. Validation and execution errors are
raised by decorators, inspectors, and machine runtime stages.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Aspects package API surface.
CONTRACT: Export aspect decorators and marker mixin used by action classes.
INVARIANTS: Keep declaration metadata deterministic for inspector/coordinator.
FLOW: decorator metadata -> inspector snapshot -> coordinator cache -> runtime execution.
FAILURES: Structural errors are enforced in decorator/inspector/machine layers.
EXTENSION POINTS: New aspect decorators must preserve metadata collection contract.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from action_machine.intents.aspects.aspect_intent import AspectIntent
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect

__all__ = [
    "AspectIntent",
    "regular_aspect",
    "summary_aspect",
]
