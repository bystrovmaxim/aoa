# src/action_machine/intents/checkers/result_date_checker.py
"""
Date result-field checker and ``result_date`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module provides two components:

1. **ResultDateChecker**: validates that a result field is either a
   ``datetime`` object or a string parsable by ``date_format``. Supports
   inclusive date range checks (``min_date`` / ``max_date``). Runtime creates
   instances from checker snapshot entries.

2. **result_date**: aspect-method decorator that writes checker metadata to
   method attribute ``_checker_meta``. Inspector/builder flow collects metadata
   into checker snapshots consumed by runtime.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_date(...)
          |
          v
    method._checker_meta append
          |
          v
    CheckerIntentInspector snapshot
          |
          v
    runtime creates ResultDateChecker
          |
          v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE AS DECORATOR
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Check date")
    @result_date("created_at", date_format="%Y-%m-%d")
    async def check_date(self, params, state, box, connections):
        return {"created_at": "2024-01-15"}

═══════════════════════════════════════════════════════════════════════════════
USAGE BY RUNTIME
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultDateChecker("created_at", date_format="%Y-%m-%d")
    checker.check({"created_at": "2024-01-15"})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — field name in aspect result dictionary.
    required : bool — whether field is required. Default ``True``.
    date_format : str | None — date parsing format (for example, ``"%Y-%m-%d"``).
                  Required when value is provided as string.
    min_date : datetime | None — minimum allowed date (inclusive).
    max_date : datetime | None — maximum allowed date (inclusive).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Accepts only ``datetime`` or formatted date string values.
- String parsing requires explicit ``date_format``.
- Range checks are inclusive for ``min_date`` / ``max_date``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``ValidationFieldError`` when:
  - value is neither ``datetime`` nor ``str``;
  - string value does not match ``date_format``;
  - parsed/provided date is outside allowed range.


AI-CORE-BEGIN
ROLE: Date checker module for aspect result fields.
CONTRACT: Validate date-like values and expose metadata via ``result_date`` decorator.
INVARIANTS: Deterministic metadata shape and strict parse/range validation rules.
FLOW: decorator metadata -> checker snapshot -> runtime checker execution.
AI-CORE-END
"""

from datetime import datetime
from typing import Any

from action_machine.intents.checkers.result_field_checker import ResultFieldChecker
from action_machine.intents.checkers.result_string_checker import _build_checker_meta
from action_machine.model.exceptions import ValidationFieldError


class ResultDateChecker(ResultFieldChecker):
    """
    Checker for ``datetime`` or formatted date-string values.
    """

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        date_format: str | None = None,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ):
        """
        Initialize date checker.

        Args:
            field_name: field name in aspect result dictionary.
            required: whether field is required.
            date_format: expected string date format (for example ``"%Y-%m-%d"``).
            min_date: minimum allowed date (inclusive).
            max_date: maximum allowed date (inclusive).
        """
        super().__init__(field_name, required)
        self.date_format = date_format
        self.min_date = min_date
        self.max_date = max_date

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Return checker constructor params for snapshot serialization.

        Returns:
            Dict with ``date_format``, ``min_date``, and ``max_date``.
        """
        return {
            "date_format": self.date_format,
            "min_date": self.min_date,
            "max_date": self.max_date,
        }

    def _parse_string(self, value: str) -> datetime:
        """
        Parse date string into ``datetime`` using configured format.

        Args:
            value: date string.

        Returns:
            Parsed ``datetime`` object.

        Raises:
            ValidationFieldError: if format is missing or parsing fails.
        """
        if self.date_format is None:
            raise ValidationFieldError(
                f"Field '{self.field_name}' contains a string value, but "
                f"date_format is required for parsing."
            )
        try:
            return datetime.strptime(value, self.date_format)
        except ValueError as exc:
            raise ValidationFieldError(
                f"Field '{self.field_name}' must match date format "
                f"'{self.date_format}'."
            ) from exc

    def _check_range(self, value: datetime) -> None:
        """
        Validate that date is inside configured inclusive range.

        Args:
            value: ``datetime`` value to validate.

        Raises:
            ValidationFieldError: if date is outside allowed range.
        """
        if self.min_date is not None and value < self.min_date:
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be greater than or equal to {self.min_date}."
            )
        if self.max_date is not None and value > self.max_date:
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be less than or equal to {self.max_date}."
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Validate type (datetime/string), parse if needed, then check range.

        Args:
            value: value to validate (guaranteed non-None by base checker).

        Raises:
            ValidationFieldError: on type, format, or range violation.
        """
        if isinstance(value, str):
            dt_value = self._parse_string(value)
        elif isinstance(value, datetime):
            dt_value = value
        else:
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be a datetime or date string, "
                f"got {type(value).__name__}."
            )
        self._check_range(dt_value)


# ═════════════════════════════════════════════════════════════════════════════
# Decorator function
# ═════════════════════════════════════════════════════════════════════════════


def result_date(
    field_name: str,
    required: bool = True,
    date_format: str | None = None,
    min_date: datetime | None = None,
    max_date: datetime | None = None,
) -> Any:
    """
    Decorator for aspect methods declaring a date result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``ResultDateChecker`` and calls ``checker.check(result_dict)``.

    Args:
        field_name: field name in aspect result dictionary.
        required: whether field is required.
        date_format: string date format (for example ``"%Y-%m-%d"``).
        min_date: minimum allowed date (inclusive).
        max_date: maximum allowed date (inclusive).

    Returns:
        Decorator function that appends checker metadata to method.

    Example:
        @regular_aspect("Check date")
        @result_date("created_at", date_format="%Y-%m-%d")
        async def check_date(self, params, state, box, connections):
            return {"created_at": "2024-01-15"}
    """
    checker = ResultDateChecker(
        field_name=field_name,
        required=required,
        date_format=date_format,
        min_date=min_date,
        max_date=max_date,
    )
    meta = _build_checker_meta(checker)

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
