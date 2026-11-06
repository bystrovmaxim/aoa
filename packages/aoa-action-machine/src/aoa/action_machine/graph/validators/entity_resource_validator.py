# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_resource_validator.py
"""
Entity resource validator — every link between entities stays inside one boundary.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An entity is a row stored by one resource (``@entity(resource=...)``). A relation is a
join or a foreign key, and a join exists only inside one database. A resource may name
the data source it shares with other resources (``PostgresResource[ShopDataSource]``);
then its boundary is that data source, and otherwise the resource itself. This pass
refuses, while the model is built, every link whose two entities have different
boundaries, so a model cannot claim a join no database can perform.

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- An association, aggregation or composition field — either side, a dictionary field
  included — names a target inside the host's boundary.
- The entity an inverse side points back to is inside the host's boundary.
- A specialization or generalization field names alternatives or a head inside the
  host's boundary.
- Every entity using one state type in its ``Lifecycle[...]`` is inside one boundary.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    NodeGraphCoordinator.build
        └── validate_entity_resources()
                ├── each @entity host: its boundary (the resource's data source, or the resource)
                ├── each relation / specialization / generalization field: target resources
                └── each Lifecycle[...] field: hosts grouped by state type
                        ↓ two boundaries
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


_BOUNDARY_RULE = "a relation stays inside one data source, or inside one resource when there is none."


def _boundary(entity: type[Any]) -> tuple[type, str]:
    """The boundary of ``entity`` — its resource's data source, or the resource — and how a message names it."""
    resource = EntityIntentResolver.resolve_resource_type(entity)
    data_source = resource.data_source_type()
    if data_source is None:
        return resource, f"{resource.__name__}, no data source"
    return data_source, f"{resource.__name__}, {data_source.__name__}"


def _check_fields(host: type[BaseEntity]) -> None:
    """Refuse the first field of ``host`` that links it to an entity of another boundary."""
    boundary, named = _boundary(host)
    for field in resolve_entity_fields(host):
        for target in _linked_entities(field):
            target_boundary, target_named = _boundary(target)
            if target_boundary is not boundary:
                raise EntityResourceError(
                    f"{host.__name__}.{field.field_name} relates {host.__name__} ({named}) "
                    f"to {target.__name__} ({target_named}): {_BOUNDARY_RULE}"
                )


def _check_state_types(users: dict[type, list[tuple[type, str]]]) -> None:
    """Refuse a state type used by entities of two boundaries, naming the first two that differ."""
    for state_type, rows in users.items():
        first_host, first_field = rows[0]
        first_boundary, first_named = _boundary(first_host)
        for host, field_name in rows[1:]:
            boundary, named = _boundary(host)
            if boundary is not first_boundary:
                raise EntityResourceError(
                    f"{state_type.__name__} is the state type of {first_host.__name__}.{first_field} "
                    f"({first_named}) and {host.__name__}.{field_name} ({named}): "
                    f"a lifecycle stays inside one data source, or inside one resource when there is none."
                )


def validate_entity_resources(entities: list[type[BaseEntity]] | None = None) -> None:
    """
    Refuse every link and every shared state type that joins entities of two boundaries.

    The boundary of an entity is the data source its resource names, or the resource itself
    when it names none.

    Args:
        entities: classes to judge; when ``None``, every loaded ``@entity`` class is used,
            including graph-excluded hosts.

    Raises:
        EntityResourceError: a relation, inverse side, specialization, generalization or
            dictionary field across boundaries, or a state type shared across boundaries.
    """
    hosts = _all_declared_entity_classes() if entities is None else entities
    state_users: dict[type, list[tuple[type, str]]] = {}
    for host in hosts:
        _check_fields(host)
        for lifecycle in LifeCycleIntentResolver.resolve_lifecycle_fields(host):
            state_type = lifecycle.lifecycle_class.state_type()
            if state_type is not None:
                state_users.setdefault(state_type, []).append((host, lifecycle.field_name))
    _check_state_types(state_users)
