# packages/aoa-action-machine/src/aoa/action_machine/exceptions/resource_entities_error.py
"""``ResourceEntitiesError`` — a resource returned an entity its ``@entities`` does not list."""

from __future__ import annotations

from typing import Any


class ResourceEntitiesError(TypeError):
    """
    AI-CORE-BEGIN
    ROLE: Runtime refusal of the return check: a resource answered with an entity it did not promise.
    CONTRACT: Names the resource, the public entry point, the path inside the answer and the exact
        class; carried by a ``TypeError`` like every AOA refusal of its kind.
    INVARIANTS: Raised when a public method of a resource returns, never at declaration; the
        comparison is by the exact class, and a relation that leads outside the list is allowed
        only when it comes back unloaded.
    AI-CORE-END

    Typical causes:

    - the returned entity's class is not listed by ``@entities``;
    - a loaded relation carries an entity of a class outside the list (even a partial one);
    - the resource declares no ``@entities`` at all.
    """

    def __init__(
        self,
        *,
        resource_name: str,
        entry_point: str,
        path: str,
        entity_class: type[Any],
        declared: bool,
    ) -> None:
        """
        Build the refusal sentence of the spec.

        Args:
            resource_name: The concrete resource class that answered.
            entry_point: The public method name that returned the answer.
            path: The path inside the answer, such as ``order.lines[0].product``.
            entity_class: The exact class of the refused entity.
            declared: Whether the resource declared ``@entities``; ``False`` makes the
                refusal say the declaration is missing rather than that the class is absent.
        """
        if declared:
            message = (
                f"{resource_name}.{entry_point} returned {entity_class.__name__} at {path}, "
                f"which @entities({resource_name}) does not list."
            )
        else:
            message = (
                f"{resource_name}.{entry_point} returned {entity_class.__name__} at {path}, "
                f"but {resource_name} declares no @entities."
            )
        super().__init__(message)
