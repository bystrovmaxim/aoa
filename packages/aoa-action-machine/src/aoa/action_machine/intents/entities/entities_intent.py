# packages/aoa-action-machine/src/aoa/action_machine/intents/entities/entities_intent.py
"""
EntitiesIntent — marker mixin and invariant helper for ``@entities``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from aoa.action_machine.intents.base_intent import BaseIntent


class EntitiesIntent(BaseIntent):
    """
    AI-CORE-BEGIN
    ROLE: Marker mixin declaring that a resource may list the entities of its database.
    CONTRACT: Presence in MRO is required by ``@entities`` target validation; every resource
        kind inherits it through ``BaseResource``.
    INVARIANTS: Holds no methods or instance state; only class-level marker semantics.
    AI-CORE-END
    """

    _entities_info: ClassVar[tuple[type[Any], ...]]


def entities_info_is_set(cls: type) -> bool:
    """
    Graph invariant: class was decorated with ``@entities`` (has its own ``_entities_info``).

    An inherited declaration is not the class's own list: the resolver and the graph link
    each resource to what it declared, so this check reads the class body, not its parents.
    """
    return "_entities_info" in cls.__dict__
