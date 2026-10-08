# packages/aoa-action-machine/src/aoa/action_machine/exceptions/condition_reason_error.py
"""``ConditionReasonError`` — a reason and its condition do not travel together."""

from __future__ import annotations


class ConditionReasonError(ValueError):
    """
    A ``reason=`` and the ``condition=`` it explains do not travel together. A refusal must say
    why it refuses, and the framework invents no reason of its own.
    """

    pass
