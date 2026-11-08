# packages/aoa-action-machine/src/aoa/action_machine/exceptions/entities_decorator_error.py
"""``EntitiesDecoratorError`` — ``@entities`` was used in a way its declaration contract refuses."""

from __future__ import annotations


class EntitiesDecoratorError(TypeError):
    """
    AI-CORE-BEGIN
    ROLE: Declaration-time refusal of the ``@entities`` resource intent.
    CONTRACT: Names the refused target or argument; carried by a ``TypeError`` because the
        mistake is written in the source, not supplied at run time.
    INVARIANTS: Raised while a resource class is declared, before any model or graph exists.
    AI-CORE-END

    Typical causes:

    - the target is not a ``BaseResource`` subclass;
    - an argument is not a class decorated with ``@entity``;
    - one entity class appears twice in the same declaration.
    """

    pass
