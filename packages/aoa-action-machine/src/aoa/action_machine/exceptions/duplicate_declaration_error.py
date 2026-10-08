# packages/aoa-action-machine/src/aoa/action_machine/exceptions/duplicate_declaration_error.py
"""``DuplicateDeclarationError`` — the same declaration was made twice."""

from __future__ import annotations


class DuplicateDeclarationError(ValueError):
    """
    The same declaration was made twice: two summary aspects on one operation, a ``@connection``
    key repeated on one resource, a ``@depends`` repeated on one class. Two declarations mean two
    answers to the same question, and the engine cannot say which one decided.
    """

    pass
