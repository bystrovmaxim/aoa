# src/action_machine/checkers/__init__.py
"""
ActionMachine checkers package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a field‑validation system for aspect results. Checkers ensure that
the dictionaries returned by regular aspects contain only declared fields and
that each field satisfies type and constraint requirements.

Each checker is composed of:
- A **checker class** (e.g., ``ResultStringChecker``) that validates a value.
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
    CheckerGateHostInspector collects _checker_meta → checker snapshot
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

- Classes using checkers must inherit ``CheckerGateHost``.
- Every field returned by a regular aspect must have a corresponding checker.
- Checker metadata is immutable and stored on the method as ``_checker_meta``.
- The machine creates checker instances per invocation; checkers are stateless.

═══════════════════════════════════════════════════════════════════════════════
EXPORTS
═══════════════════════════════════════════════════════════════════════════════

Marker mixin:
- ``CheckerGateHost``

Base class:
- ``ResultFieldChecker``

Checker classes:
- ``ResultStringChecker``   – string fields (type, length, not_empty)
- ``ResultIntChecker``      – integer fields (type, range)
- ``ResultFloatChecker``    – numeric fields int/float (type, range)
- ``ResultBoolChecker``     – boolean fields (exact isinstance(value, bool))
- ``ResultDateChecker``     – date fields (datetime or formatted string, range)
- ``ResultInstanceChecker`` – checks value against an expected class

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

    from action_machine.checkers import result_string, result_float

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
CONTRACT: Export checker classes, decorators, and gate‑host marker.
INVARIANTS: All aspect result fields must have checkers; checkers are stateless.
FLOW: decorator metadata -> inspector snapshot -> machine validation -> checker execution.
FAILURES: ValidationFieldError for missing or invalid fields.
EXTENSION POINTS: New checker types can be added by subclassing ResultFieldChecker and providing a decorator.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from .checker_gate_host import CheckerGateHost
from .result_bool_checker import ResultBoolChecker, result_bool
from .result_date_checker import ResultDateChecker, result_date
from .result_field_checker import ResultFieldChecker
from .result_float_checker import ResultFloatChecker, result_float
from .result_instance_checker import ResultInstanceChecker, result_instance
from .result_int_checker import ResultIntChecker, result_int
from .result_string_checker import ResultStringChecker, result_string

__all__ = [
    "CheckerGateHost",
    "ResultFieldChecker",
    "ResultStringChecker",
    "ResultIntChecker",
    "ResultFloatChecker",
    "ResultBoolChecker",
    "ResultDateChecker",
    "ResultInstanceChecker",
    "result_string",
    "result_int",
    "result_float",
    "result_bool",
    "result_date",
    "result_instance",
]
