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
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

Marker mixin:
- ``CheckerIntent``.

Built-in checker classes (each pairs with a ``result_*`` decorator):
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
"""

from action_machine.intents.checkers.result_bool_decorator import FieldBoolChecker, result_bool
from action_machine.intents.checkers.result_date_decorator import FieldDateChecker, result_date
from action_machine.intents.checkers.result_float_decorator import FieldFloatChecker, result_float
from action_machine.intents.checkers.result_instance_decorator import FieldInstanceChecker, result_instance
from action_machine.intents.checkers.result_int_decorator import FieldIntChecker, result_int
from action_machine.intents.checkers.result_string_decorator import FieldStringChecker, result_string
from action_machine.legacy.checker_intent import CheckerIntent

__all__ = [
    "CheckerIntent",
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
