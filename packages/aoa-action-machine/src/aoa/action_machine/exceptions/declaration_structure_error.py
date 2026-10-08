# packages/aoa-action-machine/src/aoa/action_machine/exceptions/declaration_structure_error.py
"""``DeclarationStructureError`` — intent metadata is declared on a class that does not inherit the intent base."""

from __future__ import annotations


class DeclarationStructureError(TypeError):
    """
    A class carries the metadata of an intent — aspects, checkers — without inheriting the base
    class that gives that intent meaning. The decorators were accepted, the class was not.
    """

    pass
