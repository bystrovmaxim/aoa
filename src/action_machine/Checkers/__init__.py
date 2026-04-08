# src/action_machine/checkers/__init__.py
"""
ActionMachine checkers package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Contains the field validation system for aspect results. Each checker is
represented by two components:

1. **Checker class** (ResultStringChecker, ResultIntChecker, etc.) — used by the
   machine to validate the dict returned by an aspect. The machine creates an
   instance from CheckerMeta and calls checker.check().

2. **Decorator function** (result_string, result_int, etc.) — applied to the
   aspect method and writes checker metadata to ``_checker_meta``. MetadataBuilder
   collects this metadata into ClassMetadata.checkers.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

Marker mixin:

- **CheckerGateHost** — marker mixin indicating support for checker decorators on
  aspect methods. Inherited by BaseAction.

Base class:

- **ResultFieldChecker** — base abstract checker for aspect result fields. It
defines the shared interface: check(), _check_type_and_constraints(),
  _get_extra_params().

Checker classes (used by the machine):

- **ResultStringChecker** — string fields (type, length, not_empty).
- **ResultIntChecker** — integer fields (int type, range).
- **ResultFloatChecker** — numeric fields int/float (type, range).
- **ResultBoolChecker** — boolean fields (exact isinstance(value, bool)).
- **ResultDateChecker** — date fields (datetime or formatted string, range).
- **ResultInstanceChecker** — checks value against an expected class.

Decorator functions (applied to aspect methods):

- **result_string** — declares a string field in the aspect result.
- **result_int** — declares an integer field.
- **result_float** — declares a numeric field (int/float).
- **result_bool** — declares a boolean field.
- **result_date** — declares a date field.
- **result_instance** — declares an instance-of-class field.

═══════════════════════════════════════════════════════════════════════════════
METADATA INTEGRATION
═══════════════════════════════════════════════════════════════════════════════

Decorator functions write a _checker_meta attribute on the method — a list of
metadata dicts:
    [{"checker_class": ResultStringChecker, "field_name": "txn_id",
      "required": True, ...}]

A single method can have multiple checkers (for different fields).

MetadataBuilder._collect_checkers(cls) walks the class MRO, finds methods with
_checker_meta, and collects them into ClassMetadata.checkers
(tuple[CheckerMeta]).

When ActionProductMachine executes a regular aspect:
1. It gets checkers = metadata.get_checkers_for_aspect(aspect_name).
2. If no checkers exist and the aspect returned a non-empty dict — error.
3. If checkers exist — it validates that the result contains only declared
   fields and applies each checker.

═══════════════════════════════════════════════════════════════════════════════
USAGE EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.checkers import result_string, result_int, result_float

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Payment processing")
        @result_string("txn_id", required=True, min_length=1)
        @result_float("charged_amount", required=True, min_value=0.0)
        async def process_payment(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id, "charged_amount": params.amount}

        @regular_aspect("Bonus calculation")
        @result_int("bonus_points", required=True, min_value=0)
        async def calc_bonus(self, params, state, box, connections):
            return {"bonus_points": int(params.amount * 0.1)}
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
    # Маркерный миксин
    "CheckerGateHost",
    # Базовый класс
    "ResultFieldChecker",
    # Классы чекеров (используются машиной)
    "ResultStringChecker",
    "ResultIntChecker",
    "ResultFloatChecker",
    "ResultBoolChecker",
    "ResultDateChecker",
    "ResultInstanceChecker",
    # Функции-декораторы (применяются к методам-аспектам)
    "result_string",
    "result_int",
    "result_float",
    "result_bool",
    "result_date",
    "result_instance",
]
