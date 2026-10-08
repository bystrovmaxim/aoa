# packages/aoa-action-machine/src/aoa/action_machine/exceptions/dependency_declaration_error.py
"""``DependencyDeclarationError`` — the @depends mode does not fit the target."""

from __future__ import annotations


class DependencyDeclarationError(ValueError):
    """
    The ``mode`` of a ``@depends`` does not fit its target: a ``BaseAction`` dependency needs
    ``mode=UseCase.include`` or ``mode=UseCase.extend``, a resource dependency must set none.
    """

    pass
