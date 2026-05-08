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

"""

from action_machine.intents.aspects.aspect_intent import AspectIntent
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect

__all__ = [
    "AspectIntent",
    "regular_aspect",
    "summary_aspect",
]
