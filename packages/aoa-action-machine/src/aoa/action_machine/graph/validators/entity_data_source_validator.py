# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_data_source_validator.py
"""
Entity data source validator — every stored entity has a physical place.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The model has two axes. The logical one — entities and the relations between them —
knows no store: a relation may join entities of any resources and data sources. The
physical one says where an entity lives: the resource that stores it
(``@entity(resource=...)``) and the data source that resource names
(``BaseStorage[CatalogDataSource]``). This pass refuses, while the model is built, a
resource that stores an entity and names no data source.

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- A resource named by an ``@entity`` names a data source as the type argument of its base.
- A resource that stores no entity — a gateway that only calls out — may name none.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    NodeGraphCoordinator.build / EntityGraphNode
        └── validate_entity_data_sources()
                ├── each @entity host: its resource
                └── the resource's data source
                        ↓ none
                    EntityResourceError (resource, the entities it stores)
"""

from __future__ import annotations

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.exceptions import EntityResourceError
from aoa.action_machine.graph.validators.entity_inverse_validator import _all_declared_entity_classes
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver

__all__ = ["validate_entity_data_sources"]


def validate_entity_data_sources(entities: list[type[BaseEntity]] | None = None) -> None:
    """
    Refuse a resource that stores an entity and names no data source.

    Args:
        entities: classes to judge; when ``None``, every loaded ``@entity`` class is used,
            including graph-excluded hosts.

    Raises:
        EntityResourceError: naming the first resource without a data source, sorted by name,
            and every judged entity it stores.
    """
    hosts = _all_declared_entity_classes() if entities is None else entities
    stored: dict[type, list[str]] = {}
    for host in hosts:
        resource = EntityIntentResolver.resolve_resource_type(host)
        if resource.data_source_type() is None:
            stored.setdefault(resource, []).append(host.__name__)
    if not stored:
        return
    resource = min(stored, key=lambda cls: cls.__name__)
    names = ", ".join(sorted(stored[resource]))
    raise EntityResourceError(
        f"{resource.__name__} stores {names} and names no data source: a resource that stores an entity "
        f"names its data source as the type argument of its base ({resource.__name__}(<Base>[<Name>DataSource]))."
    )
