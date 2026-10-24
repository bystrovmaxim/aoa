# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_relation_intent_resolver.py
"""EntityRelationIntentResolver — freeze one declared entity→entity relation from ``model_fields``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aoa.action_machine.intents.entity.resolved_entity_fields import (
    ResolvedEntityField,
    is_relation_container,
    resolve_entity_fields,
)

__all__ = ["EntityRelationIntentResolver", "gather_entity_relation_intent_resolvers", "is_relation_container"]


@dataclass(frozen=True)
class EntityRelationIntentResolver:
    """
    One ``BaseRelationOne`` / ``BaseRelationMany`` field on an entity host class.

    ``relation_type`` is the declarative arc (``composition`` / ``aggregation`` / ``association``).
    ``cardinality`` is ``one`` or ``many``.
    """

    field_name: str
    target_entity: type[Any]
    relation_type: str
    cardinality: str
    container_class: type[Any]
    description: str = ""
    has_inverse: bool = False
    inverse_entity: type[Any] | None = None
    inverse_field: str | None = None
    deprecated: bool = False
    omit_graph_edge: bool = False


def _from_descriptor(field: ResolvedEntityField) -> EntityRelationIntentResolver | None:
    """Build one resolver row from a resolved relation field, or ``None`` when unresolved."""
    if not field.targets or field.container is None or field.relation_kind is None:
        return None
    return EntityRelationIntentResolver(
        field_name=field.field_name,
        target_entity=field.targets[0],
        relation_type=field.relation_kind,
        cardinality=field.cardinality or "",
        container_class=field.container,
        description=field.description,
        has_inverse=field.has_inverse,
        inverse_entity=field.inverse_entity,
        inverse_field=field.inverse_field,
        deprecated=field.deprecated,
        omit_graph_edge=field.omit_graph_edge,
    )


def gather_entity_relation_intent_resolvers(host_cls: type) -> list[EntityRelationIntentResolver]:
    """Return every relation-container field on ``host_cls`` as resolver rows, in field order."""
    out: list[EntityRelationIntentResolver] = []
    for field in resolve_entity_fields(host_cls):
        if not field.is_relation:
            continue
        resolved = _from_descriptor(field)
        if resolved is not None:
            out.append(resolved)
    return out
