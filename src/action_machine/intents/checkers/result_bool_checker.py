# src/action_machine/intents/checkers/result_bool_checker.py
"""
Boolean result-field checker (:class:`FieldBoolChecker`).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validates that a result field is strictly boolean (``True``/``False``). Numeric
values (``0``, ``1``), strings (``"true"``, ``"false"``), and other types are
rejected. Runtime creates instances from checker snapshot entries. For the
``@result_bool`` decorator, see ``result_bool_decorator``.

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    checker = FieldBoolChecker("is_valid")
    checker.check({"is_valid": True})  # OK

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Accepts only ``bool`` values.
- Reuses base required/None handling from ``BaseFieldChecker``.
- Checker metadata shape is consistent with other ``result_*`` decorators.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is not ``bool``.
- Type check is strict: bool subclasses/compatible values are not coerced.

AI-CORE-BEGIN
ROLE: Boolean checker implementation for aspect result fields.
CONTRACT: Validate strict bool values; snapshot hydration matches ``result_bool`` metadata.
INVARIANTS: Deterministic metadata shape and strict ``isinstance(value, bool)`` checks.
FLOW: snapshot -> FieldBoolChecker -> check(result_dict).
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import BaseFieldChecker
from action_machine.model.exceptions import ValidationFieldError


class FieldBoolChecker(BaseFieldChecker):
    """
    Checker for strict boolean result values.

    Accepts only ``True`` / ``False`` values; no coercion from other types.
    """

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Validate that ``value`` is a strict boolean.

        Args:
            value: value to validate (guaranteed non-None by base checker).

        Raises:
            ValidationFieldError: if ``value`` is not ``bool``.
        """
        if not isinstance(value, bool):
            raise ValidationFieldError(
                f"Parameter '{self.field_name}' must be boolean, got {type(value).__name__}"
            )
