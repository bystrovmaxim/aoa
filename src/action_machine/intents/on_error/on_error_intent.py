# src/action_machine/intents/on_error/on_error_intent.py
"""
OnErrorIntent marker mixin and on-error handler validation rules.

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
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``@on_error`` handlers are NOT inherited from parent Action classes.
- Method name must end with ``"_on_error"``.
- Handler must be async.
- Signature must be exactly 6 parameters.
- Later handler cannot catch same/narrower exception types than earlier one.
- Handlers do not mutate state by contract.
- Rollup does not affect on-error processing.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        ActionMetaIntent,
        RoleIntent,
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

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    class PaymentAction(BaseAction[PayParams, PayResult]):

        @regular_aspect("Charge funds")
        async def charge_aspect(self, params, state, box, connections):
            ...

        @summary_aspect("Payment result")
        async def result_summary(self, params, state, box, connections):
            ...

        @on_error(InsufficientFundsError, description="Insufficient funds")
        async def insufficient_funds_on_error(self, params, state, box, connections, error):
            return PayResult(status="insufficient_funds", txn_id="")

        @on_error(PaymentGatewayError, description="Payment gateway error")
        async def gateway_error_on_error(self, params, state, box, connections, error):
            return PayResult(status="gateway_error", txn_id="")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from action_machine.graph.inspectors.on_error_intent_inspector import (
        OnErrorIntentInspector,
    )


class OnErrorIntent:
    """
    Marker mixin declaring support for ``@on_error`` decorator.

    Classes inheriting this mixin may declare ``@on_error`` methods for aspect
    exception handling. ``OnErrorIntentInspector`` builds snapshot consumed via
    ``GateCoordinator.get_snapshot(cls, "error_handler")``.

    AI-CORE-BEGIN
    ROLE: Marker contract for on-error handler declarations.
    CONTRACT: Carry methods with ``_on_error_meta`` written by decorator.
    INVARIANTS: Logic-free mixin used only by inspectors/validators.
    AI-CORE-END
    """

    _on_error_meta: ClassVar[dict[str, Any]]


def require_on_error_intent_marker(
    cls: type, error_handlers: list[OnErrorIntentInspector.Snapshot.ErrorHandler],
) -> None:
    """If class has @on_error handlers, it must inherit OnErrorIntent."""
    if error_handlers and not issubclass(cls, OnErrorIntent):
        handler_names = ", ".join(h.method_name for h in error_handlers)
        raise TypeError(
            f"Class {cls.__name__} declares error handlers ({handler_names}) "
            f"but does not inherit OnErrorIntent. @on_error is allowed only "
            f"on classes inheriting OnErrorIntent. Use BaseAction or add "
            f"OnErrorIntent to the inheritance chain."
        )


def _is_type_covered_by(
    candidate_type: type[Exception],
    covering_types: tuple[type[Exception], ...],
) -> bool:
    for covering in covering_types:
        if issubclass(candidate_type, covering):
            return True
    return False


def validate_error_handlers(
    cls: type,
    error_handlers: list[OnErrorIntentInspector.Snapshot.ErrorHandler],
) -> None:
    """Validate @on_error order: later handler must not be shadowed by earlier."""
    if len(error_handlers) < 2:
        return

    for i in range(1, len(error_handlers)):
        current_handler = error_handlers[i]
        for j in range(i):
            upper_handler = error_handlers[j]
            for candidate_type in current_handler.exception_types:
                if _is_type_covered_by(candidate_type, upper_handler.exception_types):
                    covering_name = next(
                        c.__name__
                        for c in upper_handler.exception_types
                        if issubclass(candidate_type, c)
                    )
                    raise TypeError(
                        f"Class {cls.__name__}: error handler "
                        f"'{current_handler.method_name}' catches "
                        f"{candidate_type.__name__}, but upper handler "
                        f"'{upper_handler.method_name}' already catches "
                        f"{covering_name}. Type {candidate_type.__name__} is "
                        f"a subclass of {covering_name} (or the same), so "
                        f"handler '{current_handler.method_name}' is unreachable. "
                        f"Move the more specific handler above the general one."
                    )
