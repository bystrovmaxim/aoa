# packages/aoa-action-machine/src/aoa/action_machine/exceptions/decorator_target_error.py
"""``DecoratorTargetError`` — the decorator was applied to something that cannot carry it."""

from __future__ import annotations


class DecoratorTargetError(TypeError):
    """
    A decorator was applied to something that cannot carry it: not a class, not a method or
    callable, or a property without a getter. The declaration never enters the graph, so the
    failure is reported where it was written.
    """

    pass
