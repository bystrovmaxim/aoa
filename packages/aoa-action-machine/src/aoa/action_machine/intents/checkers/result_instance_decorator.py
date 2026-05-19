# packages/aoa-action-machine/src/aoa/action_machine/intents/checkers/result_instance_decorator.py
"""
``result_instance`` — attach isinstance-based field checker metadata to aspect methods.

Includes :class:`FieldInstanceChecker`, which validates values with ``isinstance``
against one expected class or a tuple of classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator that appends metadata to ``method._checker_meta``. Inspector collects
snapshots; runtime builds :class:`FieldInstanceChecker` and runs ``checker.check(result_dict)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @result_instance(...)
            |
            v
    method._checker_meta append
            |
            v
    ``CheckerGraphNode`` graph node metadata
            |
            v
    runtime creates FieldInstanceChecker
            |
            v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Get user")
    @result_instance("user", User, required=True)
    async def get_user(self, params, state, box, connections):
        return {"user": User(id=1, name="John")}

    checker = FieldInstanceChecker("user", User)
    checker.check({"user": User(id=1, name="John")})  # OK
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.validation_field_error import ValidationFieldError


class FieldInstanceChecker:
    """
    Checker validating instance membership against expected class spec.

    Self-contained implementation; runtime uses the usual constructor kwargs and ``.check(result_dict)``.
    """

    __slots__ = ("expected_class", "field_name", "no_none", "required", "value_check")

    def __init__(
        self,
        field_name: str,
        expected_class: type[Any] | tuple[type[Any], ...],
        required: bool = True,
        no_none: bool = False,
        value_check: Callable[[Any], bool] | None = None,
    ) -> None:
        self.field_name = field_name
        self.required = required
        self.expected_class = expected_class
        self.no_none = no_none
        self.value_check = value_check

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Return constructor params for snapshot serialization.

        Returns:
            Dictionary with ``expected_class``, ``no_none``, and optional ``value_check``.
        """
        params: dict[str, Any] = {
            "expected_class": self.expected_class,
            "no_none": self.no_none,
        }
        if self.value_check is not None:
            params["value_check"] = self.value_check
        return params

    def check(self, result: dict[str, Any]) -> None:
        """Validate one instance-typed field in ``result``."""
        if self.field_name not in result:
            if self.required:
                raise ValidationFieldError(
                    f"Missing required parameter: '{self.field_name}'",
                    field=self.field_name,
                )
            return

        value = result[self.field_name]
        if value is None:
            if self.no_none:
                raise ValidationFieldError(
                    f"Field '{self.field_name}' must not be None",
                    field=self.field_name,
                )
            if not self.required:
                return

        if not isinstance(value, self.expected_class):
            if isinstance(self.expected_class, tuple):
                names = ", ".join(cls.__name__ for cls in self.expected_class)
                raise ValidationFieldError(
                    f"Field '{self.field_name}' must be an instance of one of: {names}, got {type(value).__name__}"
                )
            raise ValidationFieldError(
                f"Field '{self.field_name}' must be an instance of class {self.expected_class.__name__}, "
                f"got {type(value).__name__}"
            )

        if self.value_check is not None:
            if not self.value_check(value):
                raise ValidationFieldError(
                    f"Field '{self.field_name}' failed value_check",
                    field=self.field_name,
                )


def result_instance(
    field_name: str,
    expected_class: type[Any] | tuple[type[Any], ...],
    required: bool = True,
    no_none: bool = False,
    value_check: Callable[[Any], bool] | None = None,
) -> Any:
    """
    Decorator for aspect methods declaring class-instance result field.

    Writes checker metadata to method attribute ``_checker_meta``.
    Inspector/builder flow collects metadata into checker snapshots, then
    runtime creates ``FieldInstanceChecker`` and calls ``checker.check(result_dict)``.

    Args:
        field_name: field name in aspect result dictionary.
        expected_class: expected class or tuple of classes.
        required: whether field is required.
        no_none: when ``True``, reject explicit ``None`` even if the field key is present.
        value_check: optional predicate run after ``isinstance``; ``False`` raises
            ``ValidationFieldError``.

    Returns:
        Decorator function that appends checker metadata to method.

    Example:
        @regular_aspect("Get user")
        @result_instance("user", User, required=True)
        async def get_user(self, params, state, box, connections):
            return {"user": User(id=1, name="John")}

        # Multiple accepted classes:
        @regular_aspect("Get data")
        @result_instance("data", (dict, list), required=True)
        async def get_data(self, params, state, box, connections):
            return {"data": {"key": "value"}}
    """
    meta: dict[str, Any] = {
        "checker_class": FieldInstanceChecker,
        "field_name": field_name,
        "required": required,
        "no_none": no_none,
        "expected_class": expected_class,
        "value_check": value_check,
    }

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
