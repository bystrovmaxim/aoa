# tests/intents/entity/test_entity_intent_resolver.py
"""Tests for ``EntityIntentResolver`` beyond ``@entity`` scratch helpers."""

from __future__ import annotations

from typing import Annotated

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.entity import entity
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver


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


def test_resolve_entity_relations_one_association_without_inverse() -> None:
    resolver_rels = EntityIntentResolver.resolve_entity_relations(_HostEntity)
    assert len(resolver_rels) == 1
    r = resolver_rels[0]
    assert r.field_name == "other"
    assert r.target_entity is _TargetEntity
    assert r.relation_type == "association"
    assert r.cardinality == "one"
    assert r.omit_graph_edge is False
