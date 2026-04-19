# src/action_machine/intents/checkers/result_instance_checker.py
"""
Instance-type result checker (:class:`FieldInstanceChecker`).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validates that a result field is an instance of one expected class (or one class
from an expected tuple). Runtime creates checker instances from checker snapshot
entries. For the ``@result_instance`` decorator, see ``result_instance_decorator``.

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    checker = FieldInstanceChecker("user", User)
    checker.check({"user": User(id=1, name="John")})  # OK

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Uses ``isinstance`` semantics (supports inheritance).
- Supports one expected class or a tuple of accepted classes.
- Reuses required/non-null policy from ``BaseFieldChecker``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when value is not instance of expected class.
- Error message includes field name and actual type for diagnostics.

AI-CORE-BEGIN
ROLE: Instance-type checker implementation for aspect result fields.
CONTRACT: Validate instance membership; snapshot hydration matches ``result_instance`` metadata.
INVARIANTS: Deterministic metadata shape and ``isinstance``-based checks.
FLOW: snapshot -> FieldInstanceChecker -> check(result_dict).
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import BaseFieldChecker
from action_machine.model.exceptions import ValidationFieldError


class FieldInstanceChecker(BaseFieldChecker):
    """
    Checker validating instance membership against expected class spec.
    """

    def __init__(
        self,
        field_name: str,
        expected_class: type[Any] | tuple[type[Any], ...],
        required: bool = True,
    ) -> None:
        """
        Initialize instance checker.

        Args:
            field_name: field name in aspect result dictionary.
            expected_class: expected class or tuple of classes.
            required: whether field is required.
        """
        super().__init__(field_name, required)
        self.expected_class = expected_class

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Return constructor params for snapshot serialization.

        Returns:
            Dictionary with ``expected_class`` key.
        """
        return {
            "expected_class": self.expected_class,
        }

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Validate that ``value`` is instance of expected class spec.

        Args:
            value: value to validate (guaranteed non-None by base checker).

        Raises:
            ValidationFieldError: if value is not instance of expected class.
        """
        if not isinstance(value, self.expected_class):
            if isinstance(self.expected_class, tuple):
                names = ", ".join(cls.__name__ for cls in self.expected_class)
                raise ValidationFieldError(
                    f"Field '{self.field_name}' must be an instance of one of: {names}, "
                    f"got {type(value).__name__}"
                )
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be an instance of class {self.expected_class.__name__}, "
                f"got {type(value).__name__}"
            )
