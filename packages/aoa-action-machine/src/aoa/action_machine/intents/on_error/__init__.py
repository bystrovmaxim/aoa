# packages/aoa-action-machine/src/aoa/action_machine/intents/on_error/__init__.py
"""
ActionMachine on-error intent package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a mechanism for handling uncaught exceptions from Action aspects with
optional result substitution. When a regular/summary aspect raises, the runtime
searches for a matching ``@on_error`` handler by exception type and executes it.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``OnErrorIntent`` — marker mixin indicating support for ``@on_error``.
  Included by ``BaseAction``.

- ``on_error`` — method-level decorator. Accepts one exception type or a tuple
  of types and required ``description``. Writes metadata to
  ``method._on_error_meta``. :class:`~aoa.action_machine.intents.on_error.on_error_intent_resolver.OnErrorIntentResolver`
  and :func:`~aoa.action_machine.intents.on_error.on_error_intent_resolver.hydrate_error_handler_row`
  read the same shape where tests or tooling need typed rows.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    1. Aspect raises an exception (for example, ``ValueError``).
    2. ``ActionProductMachine`` stops aspect pipeline execution.
    3. Runtime iterates ``error_handlers`` top-down (declaration order).
    4. First handler whose ``exception_types`` match (``isinstance``) is called
       with ``(self, params, state, box, connections, error)``.
    5. If handler returns ``Result``, error is considered handled and returned
       result substitutes action output.
    6. If handler raises, error is wrapped into ``OnErrorHandlerError`` and
       re-raised.
    7. If no handler matches, original exception propagates as unhandled.

═══════════════════════════════════════════════════════════════════════════════
HANDLER ORDER
═══════════════════════════════════════════════════════════════════════════════

Handlers are checked in class declaration order (top-down).
Correct order: specific types first, then broad fallback.

    Valid:
        @on_error(ValueError, description="...")     <- specific
        @on_error(Exception, description="...")      <- broad fallback

    Problematic (broad handler first — specific handler never runs for that type):
        @on_error(Exception, description="...")      <- catches everything first
        @on_error(ValueError, description="...")     <- unreachable for ``ValueError``

"""

from aoa.action_machine.intents.on_error.on_error_decorator import on_error
from aoa.action_machine.intents.on_error.on_error_intent import OnErrorIntent

__all__ = [
    "OnErrorIntent",
    "on_error",
]
