# packages/aoa-action-machine/src/aoa/action_machine/intents/entities/entities_intent_resolver.py
"""EntitiesIntentResolver — resolves the ``@entities`` declaration of a resource."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.entities.entities_decorator import entities_info_tuple


class EntitiesIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve class-level ``@entities`` declarations for graph model builders and the return check.
    CONTRACT: Reads ``_entities_info`` scratch written by the decorator and returns the resource's own
        ordered tuple of entity classes; a resource that declares none resolves to ``()``.
    INVARIANTS: Never inherits a parent's list — each resource states what its own database holds; does not
        validate decorator grammar, which the decorator already refused at class definition.
    AI-CORE-END
    """

    @staticmethod
    def resolve_entities(host_cls: type) -> tuple[type[Any], ...]:
        """Return the entity classes listed by ``@entities`` on ``host_cls``, in declaration order."""
        return entities_info_tuple(host_cls)

    @staticmethod
    def resolve_entity_names(host_cls: type) -> tuple[str, ...]:
        """Return the names of the entity classes listed by ``@entities`` on ``host_cls``."""
        return tuple(entity_cls.__name__ for entity_cls in entities_info_tuple(host_cls))
