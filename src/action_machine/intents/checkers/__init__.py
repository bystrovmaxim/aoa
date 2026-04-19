# src/action_machine/intents/checkers/__init__.py
"""
ActionMachine checkers package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a field‑validation system for aspect results. Checkers ensure that
the dictionaries returned by regular aspects contain only declared fields and
that each field satisfies type and constraint requirements.

Each checker is composed of:
- A **checker class** (e.g., ``FieldStringChecker``) that validates a value.
- A **decorator** (e.g., ``result_string``) that attaches checker metadata to
  the aspect method.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @result_string("txn_id", required=True)
    async def payment_aspect(self, ...):
        return {"txn_id": "..."}

          │ decorator writes _checker_meta on method
          ▼
    CheckerIntentInspector collects _checker_meta → checker snapshot
          │
          ▼
    ActionProductMachine._apply_checkers()
          │
          ▼
    Checker instance created and invoked on aspect result dict

The machine validates that:
- The result dict contains only fields for which checkers are declared.
- Each field passes the associated checker's validation.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Classes using checkers must inherit ``CheckerIntent``.
- Every field returned by a regular aspect must have a corresponding checker.
- Checker metadata is immutable and stored on the method as ``_checker_meta``.
- The machine creates checker instances per invocation; checkers are stateless.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

Marker mixin:
- ``CheckerIntent``.

Checker base class:
- ``BaseFieldChecker``.

Built-in checker classes:
- ``FieldStringChecker``   – string fields (type, length, not_empty)
- ``FieldIntChecker``      – integer fields (type, range)
- ``FieldFloatChecker``    – numeric fields int/float (type, range)
- ``FieldBoolChecker``     – boolean fields (exact isinstance(value, bool))
- ``FieldDateChecker``     – date fields (datetime or formatted string, range)
- ``FieldInstanceChecker`` – checks value against an expected class

Decorators:
- ``result_string``
- ``result_int``
- ``result_float``
- ``result_bool``
- ``result_date``
- ``result_instance``

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.checkers import result_string, result_float

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        @regular_aspect("Process payment")
        @result_string("txn_id", required=True, min_length=1)
        @result_float("charged_amount", required=True, min_value=0.0)
        async def process_payment(self, params, state, box, connections):
            ...
            return {"txn_id": "TXN-001", "charged_amount": 100.0}

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Missing checker for a returned field raises ``ValidationFieldError``.
- Checker validation failures raise ``ValidationFieldError`` with details.
- Checkers are applied only to regular aspects; summary aspects are not checked.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Checkers package API surface.
CONTRACT: Export checker classes, decorators, and ``CheckerIntent`` marker.
INVARIANTS: All aspect result fields must have checkers; checkers are stateless.
FLOW: decorator metadata -> inspector snapshot -> machine validation -> checker execution.
FAILURES: ValidationFieldError for missing or invalid fields.
EXTENSION POINTS: New checker types can be added by subclassing ``BaseFieldChecker`` and providing a decorator.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from action_machine.intents.checkers.base_field_checker import BaseFieldChecker
from action_machine.intents.checkers.field_bool_checker import FieldBoolChecker
from action_machine.intents.checkers.field_date_checker import FieldDateChecker
from action_machine.intents.checkers.field_float_checker import FieldFloatChecker
from action_machine.intents.checkers.field_instance_checker import FieldInstanceChecker
from action_machine.intents.checkers.field_int_checker import FieldIntChecker
from action_machine.intents.checkers.field_string_checker import FieldStringChecker
from action_machine.intents.checkers.result_bool_decorator import result_bool
from action_machine.intents.checkers.result_date_decorator import result_date
from action_machine.intents.checkers.result_float_decorator import result_float
from action_machine.intents.checkers.result_instance_decorator import result_instance
from action_machine.intents.checkers.result_int_decorator import result_int
from action_machine.intents.checkers.result_string_decorator import result_string
from action_machine.legacy.checker_intent import CheckerIntent

__all__ = [
    "CheckerIntent",
    "BaseFieldChecker",
    "FieldStringChecker",
    "FieldIntChecker",
    "FieldFloatChecker",
    "FieldBoolChecker",
    "FieldDateChecker",
    "FieldInstanceChecker",
    "result_string",
    "result_int",
    "result_float",
    "result_bool",
    "result_date",
    "result_instance",
]
