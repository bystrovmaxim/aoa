# src/action_machine/intents/checkers/checker_intent.py
"""
Checker intent marker and checker-attachment validators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``CheckerIntent`` marks classes that may use checker decorators (for example,
``@result_string``) on aspect methods. Validators in this module enforce:
1) marker presence when checkers are declared, and
2) checker-to-aspect binding correctness.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        CheckRolesIntent,
        DependencyIntent[object],
        CheckerIntent,                ← marker: allows checkers on methods
        AspectIntent,
        ConnectionIntent,
    ): ...

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Payment processing")
        @result_string("txn_id", "Transaction ID", required=True)
        async def process_payment(self, params, state, box, connections):
            ...
            return {"txn_id": txn_id}

    @result_* decorators
            |
            v
    method._checker_meta entries
            |
            v
    CheckerIntentInspector collection
            |
            v
    require_checker_intent_marker(...)
    validate_checkers_belong_to_aspects(...)
            |
            v
    checker facet snapshot -> runtime checker execution
"""

from __future__ import annotations

from typing import Any, ClassVar


class CheckerIntent:
    """
    Marker mixin indicating support for checker decorators.

    Classes inheriting this mixin may declare checker decorators on aspect methods.
    The mixin itself has no behavior; it is a marker contract for inspectors.
    """

    # Mypy annotation retained for compatibility checks.
    _field_checkers: ClassVar[list[Any]]


def require_checker_intent_marker(cls: type, checkers: list[Any]) -> None:
    """Require ``CheckerIntent`` marker when checkers are declared."""
    if checkers and not issubclass(cls, CheckerIntent):
        checker_fields = ", ".join(c.field_name for c in checkers)
        raise TypeError(
            f"Class {cls.__name__} declares checkers for fields ({checker_fields}) "
            f"but does not inherit CheckerIntent. Checker decorators "
            f"(@result_string, @result_int, etc.) are allowed only on classes "
            f"inheriting CheckerIntent. Use BaseAction or add CheckerIntent to "
            f"the inheritance chain."
        )


def validate_checkers_belong_to_aspects(
    cls: type,
    checkers: list[Any],
    aspects: list[Any],
) -> None:
    """Validate that each checker is attached to an existing aspect method."""
    aspect_names = {a.method_name for a in aspects}
    for checker in checkers:
        if checker.method_name not in aspect_names:
            raise ValueError(
                f"Class {cls.__name__}: checker '{checker.checker_class.__name__}' "
                f"for field '{checker.field_name}' is attached to method "
                f"'{checker.method_name}', which is not an aspect method. "
                f"Checkers may be applied only to methods decorated with "
                f"@regular_aspect or @summary_aspect."
            )
