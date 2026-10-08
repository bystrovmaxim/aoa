# packages/aoa-action-machine/src/aoa/action_machine/exceptions/missing_declaration_error.py
"""``MissingDeclarationError`` — a resolver needs a declaration the class does not carry."""

from __future__ import annotations


class MissingDeclarationError(ValueError):
    """
    A resolver needs a declaration the class does not carry — a description, a ``target_aspect``,
    or a lifecycle template — and the graph cannot be resolved without it.
    """

    pass
