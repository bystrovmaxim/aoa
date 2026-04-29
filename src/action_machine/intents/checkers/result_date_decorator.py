# src/action_machine/intents/checkers/result_date_decorator.py
"""
``result_date`` — attach date/datetime field checker metadata to aspect methods.

Includes :class:`FieldDateChecker`, which validates ``datetime`` or formatted date
strings with optional inclusive ``min_date`` / ``max_date`` bounds.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator that appends metadata to ``method._checker_meta``. Inspector collects
snapshots; runtime builds :class:`FieldDateChecker` and runs ``checker.check(result_dict)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_date(...)
          |
          v
    method._checker_meta append
          |
          v
    ``CheckerGraphNode`` facet metadata
          |
          v
    runtime creates FieldDateChecker
          |
          v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Check date")
    @result_date("created_at", date_format="%Y-%m-%d")
    async def check_date(self, params, state, box, connections):
        return {"created_at": "2024-01-15"}

    checker = FieldDateChecker("created_at", date_format="%Y-%m-%d")
    checker.check({"created_at": "2024-01-15"})  # OK
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from action_machine.exceptions import ValidationFieldError


class FieldDateChecker:
    """
    Checker for ``datetime`` or formatted date-string values.

    Self-contained implementation; runtime uses the usual constructor kwargs and ``.check(result_dict)``.
    """

    __slots__ = ("date_format", "field_name", "max_date", "min_date", "required")

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        date_format: str | None = None,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ) -> None:
        self.field_name = field_name
        self.required = required
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

    def check(self, result: dict[str, Any]) -> None:
        """Validate one date/datetime field in ``result``."""
        value = result.get(self.field_name)
        if value is None:
            if self.required:
                raise ValidationFieldError(
                    f"Missing required parameter: '{self.field_name}'",
                    field=self.field_name,
                )
            return
        if isinstance(value, str):
            dt_value = self._parse_string(value)
        elif isinstance(value, datetime):
            dt_value = value
        else:
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be a datetime or date string, got {type(value).__name__}."
            )
        self._check_range(dt_value)

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
                f"Field '{self.field_name}' contains a string value, but date_format is required for parsing."
            )
        try:
            return datetime.strptime(value, self.date_format)
        except ValueError as exc:
            raise ValidationFieldError(
                f"Field '{self.field_name}' must match date format '{self.date_format}'."
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
            raise ValidationFieldError(f"Field '{self.field_name}' must be greater than or equal to {self.min_date}.")
        if self.max_date is not None and value > self.max_date:
            raise ValidationFieldError(f"Field '{self.field_name}' must be less than or equal to {self.max_date}.")


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
    runtime creates ``FieldDateChecker`` and calls ``checker.check(result_dict)``.

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
    meta: dict[str, Any] = {
        "checker_class": FieldDateChecker,
        "field_name": field_name,
        "required": required,
        "date_format": date_format,
        "min_date": min_date,
        "max_date": max_date,
    }

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
