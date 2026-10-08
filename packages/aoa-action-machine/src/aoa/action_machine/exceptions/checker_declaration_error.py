# packages/aoa-action-machine/src/aoa/action_machine/exceptions/checker_declaration_error.py
"""``CheckerDeclarationError`` — a checker is attached to something that cannot carry it."""

from __future__ import annotations


class CheckerDeclarationError(ValueError):
    """
    A result checker is attached to a method that is not an aspect method. Checkers read the
    result a step produced, so they belong to steps.
    """

    pass
