# packages/aoa-action-machine/src/aoa/action_machine/exceptions/decorator_argument_value_error.py
"""``DecoratorArgumentValueError`` — a decorator argument has an unusable value."""

from __future__ import annotations


class DecoratorArgumentValueError(ValueError):
    """
    A decorator argument has the right type and an unusable value: negative where a count is
    expected, out of range, empty, or blank.
    """

    pass
