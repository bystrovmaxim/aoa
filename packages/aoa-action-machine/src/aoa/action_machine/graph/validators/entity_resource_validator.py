# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_resource_validator.py
"""
Entity resource validator — every link between entities stays inside one resource.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An entity is a row stored by one resource (``@entity(resource=...)``). A relation is a
join or a foreign key, and a join exists only inside one database. This pass refuses,
while the model is built, every link whose two entities are stored by different
resources, so a model cannot claim a join no database can perform.

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- An association, aggregation or composition field — either side, a dictionary field
  included — names a target stored by the host's resource.
- The entity an inverse side points back to is stored by the host's resource.
- A specialization or generalization field names alternatives or a head stored by the
  host's resource.
- A state type is stored by the resource of the entities whose ``Lifecycle[...]`` uses
  it: every entity using one state type is stored by one resource.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    NodeGraphCoordinator.build
        └── validate_entity_resources()
                ├── each @entity host: its resource
                ├── each relation / specialization / generalization field: target resources
                └── each Lifecycle[...] field: hosts grouped by state type
                        ↓ two resources
                    EntityResourceError (link, both entities, both resources)

A target without ``@entity`` is not judged here: the field validator that runs first
names it.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.exceptions import EntityResourceError
from aoa.action_machine.graph.validators.entity_inverse_validator import _all_declared_entity_classes
from aoa.action_machine.intents.entity.entity_intent import entity_info_is_set
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.entity.lifecycle_intent_resolver import LifeCycleIntentResolver
from aoa.action_machine.intents.entity.resolved_entity_fields import ResolvedEntityField, resolve_entity_fields

__all__ = ["validate_entity_resources"]


def _linked_entities(field: ResolvedEntityField) -> list[type[Any]]:
    """Every entity class one field links its host to: targets, dictionary and inverse endpoint."""
    if not (field.is_relation or field.is_specialization or field.is_generalization or field.dictionary):
        return []
    linked = list(field.targets)
    if field.dictionary is not None:
        linked.append(field.dictionary)
    if field.has_inverse and field.inverse_entity is not None:
        linked.append(field.inverse_entity)
    return [target for target in linked if isinstance(target, type) and entity_info_is_set(target)]


def _check_fields(host: type[BaseEntity], resource: type) -> None:
    """Refuse the first field of ``host`` that links it to an entity of another resource."""
    for field in resolve_entity_fields(host):
        for target in _linked_entities(field):
            target_resource = EntityIntentResolver.resolve_resource_type(target)
            if target_resource is not resource:
                raise EntityResourceError(
                    f"{host.__name__}.{field.field_name} relates {host.__name__} ({resource.__name__}) "
                    f"to {target.__name__} ({target_resource.__name__}): a relation stays inside one resource."
                )


def _check_state_types(users: dict[type, list[tuple[type, str, type]]]) -> None:
    """Refuse a state type used by entities of two resources, naming the first two that differ."""
    for state_type, rows in users.items():
        first_host, first_field, first_resource = rows[0]
        for host, field_name, resource in rows[1:]:
            if resource is not first_resource:
                raise EntityResourceError(
                    f"{state_type.__name__} is the state type of {first_host.__name__}.{first_field} "
                    f"({first_resource.__name__}) and {host.__name__}.{field_name} ({resource.__name__}): "
                    f"a lifecycle stays inside one resource."
                )


def validate_entity_resources(entities: list[type[BaseEntity]] | None = None) -> None:
    """
    Refuse every link and every shared state type that joins entities of two resources.

    Args:
        entities: classes to judge; when ``None``, every loaded ``@entity`` class is used,
            including graph-excluded hosts.

    Raises:
        EntityResourceError: a relation, inverse side, specialization, generalization or
            dictionary field across resources, or a state type shared across resources.
    """
    hosts = _all_declared_entity_classes() if entities is None else entities
    state_users: dict[type, list[tuple[type, str, type]]] = {}
    for host in hosts:
        resource = EntityIntentResolver.resolve_resource_type(host)
        _check_fields(host, resource)
        for lifecycle in LifeCycleIntentResolver.resolve_lifecycle_fields(host):
            state_type = lifecycle.lifecycle_class.state_type()
            if state_type is not None:
                state_users.setdefault(state_type, []).append((host, lifecycle.field_name, resource))
    _check_state_types(state_users)
