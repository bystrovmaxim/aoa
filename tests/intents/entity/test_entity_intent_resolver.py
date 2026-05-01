# tests/intents/entity/test_entity_intent_resolver.py
"""Tests for ``EntityIntentResolver`` beyond ``@entity`` scratch helpers."""

from __future__ import annotations

from typing import Annotated

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.entity import entity
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from action_machine.legacy.entity_intent_inspector import collect_entity_relations


class _TDomain(BaseDomain):
    name = "t"
    description = "t"


@entity(description="Target", domain=_TDomain)
class _TargetEntity(BaseEntity):
    id: str


@entity(description="Host", domain=_TDomain)
class _HostEntity(BaseEntity):
    id: str
    other: Annotated[AssociationOne[_TargetEntity], NoInverse()] = Rel(
        description="link",
    )  # type: ignore[assignment]


_TargetEntity.model_rebuild()
_HostEntity.model_rebuild()


def test_resolve_entity_relations_aligns_with_collector() -> None:
    resolver_rels = EntityIntentResolver.resolve_entity_relations(_HostEntity)
    legacy = collect_entity_relations(_HostEntity)
    assert len(resolver_rels) == len(legacy) == 1
    r, legacy_r = resolver_rels[0], legacy[0]
    assert r.field_name == legacy_r.field_name == "other"
    assert r.target_entity is legacy_r.target_entity is _TargetEntity
    assert r.relation_type == legacy_r.relation_type
    assert r.cardinality == legacy_r.cardinality == "one"
    assert r.omit_graph_edge == legacy_r.omit_graph_edge
