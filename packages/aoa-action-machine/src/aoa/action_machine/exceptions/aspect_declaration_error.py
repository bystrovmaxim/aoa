# packages/aoa-action-machine/src/aoa/action_machine/exceptions/aspect_declaration_error.py
"""``AspectDeclarationError`` — the shape of the aspect pipeline is wrong."""

from __future__ import annotations


class AspectDeclarationError(ValueError):
    """
    The aspect pipeline is not a pipeline: regular aspects without a summary aspect to end it, or
    a summary aspect that is not declared last.
    """

    pass
