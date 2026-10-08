# packages/aoa-action-machine/src/aoa/action_machine/exceptions/description_type_error.py
"""``DescriptionTypeError`` — a description is not a string."""

from __future__ import annotations


class DescriptionTypeError(TypeError):
    """
    A declared description is not a string. Every intent that asks the developer to say what a
    step, a check or a handler does refuses a value that cannot be read as that sentence.
    """

    pass
