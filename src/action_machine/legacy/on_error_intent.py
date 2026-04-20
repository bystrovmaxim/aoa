# src/action_machine/legacy/on_error_intent.py
"""
OnErrorIntent marker mixin for ``@on_error`` handlers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``OnErrorIntent`` marks classes that support ``@on_error`` handlers for uncaught
aspect exceptions. ``BaseAction`` inherits this mixin.

Presence of ``OnErrorIntent`` in class MRO documents contract:
"this class may declare @on_error methods".

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

When regular/summary aspect raises, ActionProductMachine:

1. Stops aspect pipeline execution.
2. Iterates ``@on_error`` handlers top-down (declaration order).
3. Invokes first handler whose type list matches via ``isinstance`` with
   ``(self, params, state, box, connections, error)``.
4. If handler returns ``Result``, action result is substituted.
5. If handler raises, runtime wraps into ``OnErrorHandlerError`` and propagates.
6. If no handler matches, original exception propagates unhandled.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        ActionMetaIntent,
        CheckRolesIntent,
        DependencyIntent[object],
        CheckerIntent,
        AspectIntent,
        ConnectionIntent,
        OnErrorIntent,                <- marker: enables @on_error
    ): ...

    @meta(description="Create order", domain=OrdersDomain)
    @check_roles(NoneRole)
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Validation")
        async def validate_aspect(self, params, state, box, connections):
            ...

        @summary_aspect("Result")
        async def build_result_summary(self, params, state, box, connections):
            ...

        @on_error(ValueError, description="Handle validation error")
        async def handle_validation_on_error(self, params, state, box, connections, error):
            return OrderResult(order_id="ERR", status="validation_failed", total=0)

    # @on_error decorator writes into method:
    #   method._on_error_meta = {
    #       "exception_types": (ValueError,),
    #       "description": "Handle validation error",
    #   }
    #
    # OnErrorIntentInspector collects error_handler snapshot:
    #   coordinator.get_snapshot(CreateOrderAction, "error_handler") ->
    #   (ErrorHandler(method_name="handle_validation_on_error",
    #                exception_types=(ValueError,), description="...",
    #                method_ref=<func>),)
    #
    # ActionProductMachine on aspect failure:
    #   1. Finds first matching handler by isinstance(error, exc_types).
    #   2. Calls handler(action, params, state, box, connections, error).
    #   3. If handler returns Result, substitutes output.

"""

from __future__ import annotations

from typing import Any, ClassVar


class OnErrorIntent:
    """
AI-CORE-BEGIN
    ROLE: Marker contract for on-error handler declarations.
    CONTRACT: Carry methods with ``_on_error_meta`` written by decorator.
    INVARIANTS: Logic-free mixin used only by inspectors/validators.
    AI-CORE-END
"""

    _on_error_meta: ClassVar[dict[str, Any]]
