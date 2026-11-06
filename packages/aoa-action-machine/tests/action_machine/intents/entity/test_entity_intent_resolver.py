# tests/intents/entity/test_entity_intent_resolver.py
"""Tests for ``EntityIntentResolver`` beyond ``@entity`` scratch helpers."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseAssocEntity, NoInverse
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import InMemoryDataSource
from aoa.action_machine.resources.base_storage import BaseStorage


class _TDomain(BaseDomain):
    name = "t"
    description = "t"


@meta(description="Where _TStorage keeps its rows")
class _TDataSource(InMemoryDataSource):
    """The store _TStorage works with."""


@meta(description="Stores the t entities", domain=_TDomain)
class _TStorage(BaseStorage[_TDataSource]):
    """Hold the t entities."""


@entity(description="Target", resource=_TStorage)
class _TargetAssocEntity(BaseAssocEntity):
    id: str


@entity(description="Host", resource=_TStorage)
class _HostAssocEntity(BaseAssocEntity):
    id: str
    other: Annotated[AssociationOne[_TargetAssocEntity], NoInverse()] = Field(
        description="link",
    )  # type: ignore[assignment]


_TargetAssocEntity.model_rebuild()
_HostAssocEntity.model_rebuild()


def test_resolve_entity_relations_one_association_without_inverse() -> None:
    resolver_rels = EntityIntentResolver.resolve_entity_relations(_HostAssocEntity)
    assert len(resolver_rels) == 1
    r = resolver_rels[0]
    assert r.field_name == "other"
    assert r.target_entity is _TargetAssocEntity
    assert r.relation_type == "association"
    assert r.cardinality == "one"
    assert r.omit_graph_edge is False
