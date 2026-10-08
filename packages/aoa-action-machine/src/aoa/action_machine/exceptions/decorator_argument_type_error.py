# packages/aoa-action-machine/src/aoa/action_machine/exceptions/decorator_argument_type_error.py
"""``DecoratorArgumentTypeError`` — a decorator argument has the wrong type."""

from __future__ import annotations


class DecoratorArgumentTypeError(TypeError):
    """
    A decorator argument has the wrong type. The message names the decorator and the argument;
    the value the caller passed is in it too, so the fix is at the call site.
    """

    pass
