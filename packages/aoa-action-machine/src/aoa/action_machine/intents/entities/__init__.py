# packages/aoa-action-machine/src/aoa/action_machine/intents/entities/__init__.py
"""
Entities intent package — ``@entities`` marker, decorator, and graph resolver.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@entities(*classes)`` declares the entities that lie in a resource's database
and that the resource may assemble. The declaration is a resource intent of its
own: it writes ``_entities_info`` and is read by
:class:`~aoa.action_machine.intents.entities.entities_intent_resolver.EntitiesIntentResolver`.

Every argument must be a class decorated with ``@entity``; a class repeated in one
declaration is refused, and an empty list is allowed. Every resource kind
(``BaseStorage``, ``BaseGateway``, ``BaseController``) may declare it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @entities(OrderCoreEntity, CustomerCoreEntity)
            │
            ▼  writes cls._entities_info (ordered tuple)
    EntitiesIntentResolver.resolve_entities(resource_cls)
            │
            ▼
    return check and, from protocol 2.0, one resource_entity edge per listed entity

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.intents.entities import entities
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources import BaseStorage

    @meta(description="The shop database")
    @entities(OrderCoreEntity, CustomerCoreEntity)
    class ShopDatabaseStorage(BaseStorage):
        pass
"""

from __future__ import annotations

from aoa.action_machine.intents.entities.entities_decorator import (
    EntitiesDecoratorError,
    entities,
    entities_info_tuple,
)
from aoa.action_machine.intents.entities.entities_intent import (
    EntitiesIntent,
    entities_info_is_set,
)
from aoa.action_machine.intents.entities.entities_intent_resolver import EntitiesIntentResolver

__all__ = [
    "EntitiesDecoratorError",
    "EntitiesIntent",
    "EntitiesIntentResolver",
    "entities",
    "entities_info_is_set",
    "entities_info_tuple",
]
